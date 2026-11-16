#!/usr/bin/env python3
"""Crea en Oracle Cloud (Always Free) la red y la VM del servidor RemoteDesk.

Idempotente: reutiliza la VCN/subred/VM si ya existen. Si Oracle responde
"Out of capacity" (habitual en la capa gratis), reintenta cada RETRY_SECONDS
hasta conseguirla. Solo usa formas Always Free.

Requisitos: pip install oci ; ~/.oci/config con una API key válida.
Uso: python infra/oci_provision.py [--ssh-pub ~/.ssh/remotedesk_oracle.pub]
"""
import argparse
import base64
import os
import sys
import time

import oci

NAME = "remotedesk"
RETRY_SECONDS = 180
REPO_RAW = "https://raw.githubusercontent.com/brayanmeneses-pixel/remotedesk/main"
CLOUD_INIT = f"""#!/bin/bash
curl -fsSL {REPO_RAW}/infra/setup.sh -o /root/setup.sh
REPO_RAW={REPO_RAW} bash /root/setup.sh > /var/log/remotedesk-setup.log 2>&1
"""
# (forma, ocpus, memoria GB, imagen-arch) en orden de preferencia; todas Always Free.
SHAPES = [
    ("VM.Standard.A1.Flex", 1, 6),
    ("VM.Standard.E2.1.Micro", None, None),
]


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def first(items, pred):
    return next((x for x in items if pred(x)), None)


def ensure_network(cfg, net):
    comp = cfg["tenancy"]
    vcn = first(net.list_vcns(comp).data, lambda v: v.display_name == f"{NAME}-vcn" and v.lifecycle_state == "AVAILABLE")
    if not vcn:
        log("creando VCN")
        vcn = net.create_vcn(oci.core.models.CreateVcnDetails(
            compartment_id=comp, cidr_blocks=["10.0.0.0/16"], display_name=f"{NAME}-vcn", dns_label=NAME)).data
        vcn = oci.wait_until(net, net.get_vcn(vcn.id), "lifecycle_state", "AVAILABLE").data
    igw = first(net.list_internet_gateways(comp, vcn_id=vcn.id).data, lambda g: g.lifecycle_state == "AVAILABLE")
    if not igw:
        log("creando internet gateway")
        igw = net.create_internet_gateway(oci.core.models.CreateInternetGatewayDetails(
            compartment_id=comp, vcn_id=vcn.id, is_enabled=True, display_name=f"{NAME}-igw")).data
        igw = oci.wait_until(net, net.get_internet_gateway(igw.id), "lifecycle_state", "AVAILABLE").data
    net.update_route_table(vcn.default_route_table_id, oci.core.models.UpdateRouteTableDetails(route_rules=[
        oci.core.models.RouteRule(destination="0.0.0.0/0", destination_type="CIDR_BLOCK", network_entity_id=igw.id)]))

    def tcp(lo, hi):
        return oci.core.models.IngressSecurityRule(protocol="6", source="0.0.0.0/0", tcp_options=oci.core.models.TcpOptions(
            destination_port_range=oci.core.models.PortRange(min=lo, max=hi)))
    ingress = [
        tcp(22, 22),
        tcp(21115, 21117),
        oci.core.models.IngressSecurityRule(protocol="17", source="0.0.0.0/0", udp_options=oci.core.models.UdpOptions(
            destination_port_range=oci.core.models.PortRange(min=21116, max=21116))),
        oci.core.models.IngressSecurityRule(protocol="1", source="0.0.0.0/0",
                                            icmp_options=oci.core.models.IcmpOptions(type=3, code=4)),
    ]
    egress = [oci.core.models.EgressSecurityRule(protocol="all", destination="0.0.0.0/0")]
    net.update_security_list(vcn.default_security_list_id, oci.core.models.UpdateSecurityListDetails(
        ingress_security_rules=ingress, egress_security_rules=egress))
    log("firewall de Oracle: TCP 22, 21115-21117; UDP 21116")

    sub = first(net.list_subnets(comp, vcn_id=vcn.id).data, lambda s: s.display_name == f"{NAME}-subnet" and s.lifecycle_state == "AVAILABLE")
    if not sub:
        log("creando subred pública")
        sub = net.create_subnet(oci.core.models.CreateSubnetDetails(
            compartment_id=comp, vcn_id=vcn.id, cidr_block="10.0.0.0/24", display_name=f"{NAME}-subnet",
            dns_label="pub", prohibit_public_ip_on_vnic=False,
            route_table_id=vcn.default_route_table_id, security_list_ids=[vcn.default_security_list_id])).data
        sub = oci.wait_until(net, net.get_subnet(sub.id), "lifecycle_state", "AVAILABLE").data
    return sub


def find_image(compute, comp, shape):
    imgs = compute.list_images(comp, operating_system="Canonical Ubuntu", operating_system_version="24.04",
                               shape=shape, sort_by="TIMECREATED", sort_order="DESC").data
    imgs = [i for i in imgs if "Minimal" not in i.display_name]
    return imgs[0] if imgs else None


def public_ip(cfg, compute, net, inst):
    for att in compute.list_vnic_attachments(cfg["tenancy"], instance_id=inst.id).data:
        v = net.get_vnic(att.vnic_id).data
        if v.public_ip:
            return v.public_ip
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ssh-pub", default=os.path.expanduser("~/.ssh/remotedesk_oracle.pub"))
    args = ap.parse_args()
    cfg = oci.config.from_file()
    comp = cfg["tenancy"]
    ident = oci.identity.IdentityClient(cfg)
    compute = oci.core.ComputeClient(cfg)
    net = oci.core.VirtualNetworkClient(cfg)
    ssh_pub = open(args.ssh_pub, encoding="utf-8").read().strip()

    existing = first(compute.list_instances(comp).data,
                     lambda i: i.display_name == f"{NAME}-server" and i.lifecycle_state not in ("TERMINATED", "TERMINATING"))
    if existing:
        inst = oci.wait_until(compute, compute.get_instance(existing.id), "lifecycle_state", "RUNNING", max_wait_seconds=900).data
        log(f"VM ya existe: {inst.shape}")
        print(f"PUBLIC_IP={public_ip(cfg, compute, net, inst)}", flush=True)
        return

    sub = ensure_network(cfg, net)
    ads = [a.name for a in ident.list_availability_domains(comp).data]
    available_shapes = {s.shape for s in compute.list_shapes(comp).data}
    candidates = [s for s in SHAPES if s[0] in available_shapes]
    log(f"dominios: {ads}; formas gratis disponibles en la región: {[c[0] for c in candidates]}")
    if not candidates:
        sys.exit("La región no ofrece formas Always Free.")

    attempt = 0
    while True:
        attempt += 1
        for shape, ocpus, mem in candidates:
            img = find_image(compute, comp, shape)
            if not img:
                log(f"sin imagen Ubuntu 24.04 para {shape}")
                continue
            for ad in ads:
                details = oci.core.models.LaunchInstanceDetails(
                    compartment_id=comp, availability_domain=ad, shape=shape, display_name=f"{NAME}-server",
                    source_details=oci.core.models.InstanceSourceViaImageDetails(image_id=img.id, boot_volume_size_in_gbs=50),
                    create_vnic_details=oci.core.models.CreateVnicDetails(subnet_id=sub.id, assign_public_ip=True),
                    metadata={"ssh_authorized_keys": ssh_pub,
                              "user_data": base64.b64encode(CLOUD_INIT.encode()).decode()})
                if ocpus:
                    details.shape_config = oci.core.models.LaunchInstanceShapeConfigDetails(ocpus=ocpus, memory_in_gbs=mem)
                try:
                    inst = compute.launch_instance(details).data
                except oci.exceptions.ServiceError as e:
                    log(f"intento {attempt} {shape} {ad}: {e.status} {e.code} {e.message[:90]}")
                    continue
                log(f"¡VM creada! {shape} en {ad}; esperando RUNNING")
                inst = oci.wait_until(compute, compute.get_instance(inst.id), "lifecycle_state", "RUNNING",
                                      max_wait_seconds=900).data
                print(f"PUBLIC_IP={public_ip(cfg, compute, net, inst)}", flush=True)
                return
        time.sleep(RETRY_SECONDS)


if __name__ == "__main__":
    main()
