# Create Site-to-site VPN - ASA to Azure

Builds a route-based IKEv2 site-to-site VPN between a Cisco ASA and an Azure VPN gateway.

- **Azure:** resource group, virtual network, subnets, GatewaySubnet, public IP, VPN gateway (route-based, *VpnGw1AZ*), local network gateway and VPN connection
- **ASA:** object-groups, IKEv2 policy, IPsec proposal and profile, VTI (*Tunnel1*) and its ACL, static routes (to the Azure address spaces) and tunnel-group

When run in full from behind the ASA, the playbook looks up the ASA and Azure public IPs. Either can be overridden in *group_vars/all.yml* or with `-e`.

| Variable | What it is | Looked up from | Set it yourself when |
| --- | --- | --- | --- |
| `rmte_public_ip` | ASA public IP | `ipify`, so run from a host behind the ASA | The Ansible host isn't behind the ASA |
| `cld_public_ip` | Azure public IP | Azure (`az_public_ip_name`) | Running only the ASA part, or Azure has already been deleted |

### Versions

- ASA: tested on ASAv 9.22(2)14
- ansible-core: 2.21.5
- Python: 3.14
- Collections: azure.azcollection 4.2.0, cisco.asa 7.0.0

### Prerequisites

1. Install the Python packages (ansible-core, ansible-lint and the Azure SDK) from *pyproject.toml*\
   `uv sync`

2. Install the collections into the project (*./collections*, git ignored)\
   `uv run ansible-galaxy collection install -r collections/requirements.yml`

3. Install the [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) (macOS: `brew install azure-cli`)

4. Log in to Azure and check the subscription (*azure.azcollection* modules fall back to the CLI session and the *az* CLI tasks use it directly)\
   `az login`\
   `az account show`

5. On the ASA, enable SSH with an ECDSA host key. paramiko 5.x no longer accepts the ASA's default *ssh-rsa*\
   `ssh key-exchange hostkey ecdsa`

The ASA credentials are in *group_vars/all.yml*, Azure uses your local *az login* session (CI or unattended runs need service principal environment variables).

### Variables

All the variables are in *group_vars/all.yml*, split into ASA, Azure and both.

#### ASA variables

- *ansible_user:* ASA username
- *ansible_password:* ASA password
- *asa_vpn_index:* Priority of the IKEv2 policy
- *asa_vpn_interface:* Outside interface (nameif). IKEv2 is enabled on it and it is the tunnel source
- *asa_tunnel_intf:* Nameif of *Tunnel1*. The static routes to Azure point out of it
- *asa_tunnel_ip:* /30 for the tunnel. The ASA uses the first address, the second is the next hop of the static routes
- *asa_tunnel_acl:* Name of the ACL on the tunnel nameif that allows the Azure subnets in (only matters with `no sysopt connection permit-vpn`)
- *asa_vpn.local_grp:* Object-group of the networks behind the ASA (*rmte_subnets*), used in the tunnel ACL
- *asa_vpn.az_subnet_grp:* Object-group of the Azure subnets (*az_subnets*), used in the tunnel ACL

#### Azure variables

- *az_region:* Azure region for all the VPN objects
- *az_rg_name:* Resource group name
- *az_public_ip_name:* Name of the VPN gateway's public IP
- *az_vn_name:* Virtual network name
- *az_gw_subnet_prfx:* Gateway subnet prefix. Must be inside *az_vn_addr_spc* and not overlap *az_subnets*. Azure recommends /27
- *az_gateway:* VPN gateway name. It joins the public IP and the gateway subnet
- *az_rmte_gateway:* Local network gateway name. It holds the ASA's public IP and the networks behind it
- *az_vpn_connection:* VPN connection name. It links the VPN gateway to the local network gateway and holds the PSK and IPsec policy

#### Variables for both ends

- *cld_provider:* Short name of the cloud end (*AZ*), used in the ASA and Azure object names
- *rmte_location:* Short name of the ASA site (*HME*), used in the Azure object names
- *rmte_subnets:* Networks behind the ASA. Used in the ASA object-group and the Azure local network gateway
- *az_vn_addr_spc:* Address spaces (supernets) of the Azure virtual network. The ASA has a static route for each one over *Tunnel1*
- *az_subnets:* Subnets in the virtual network (*name: prefix*). The tunnel ACL allows these in
- *psk:* Pre-shared key, set on both ends
- *rmte_public_ip:* ASA public IP. Commented out so it is dynamically looked up (see [Setting the public IPs yourself](#setting-the-public-ips-yourself))
- *cld_public_ip:* Azure public IP. Commented out so it is dynamically looked up (see [Setting the public IPs yourself](#setting-the-public-ips-yourself))

#### Crypto variables

The same values build the ASA config and the Azure IPsec policy, so both ends always match.

| Variable | What it is | Options |
| --- | --- | --- |
| *p1_encr* | Phase 1 encryption | aes-192, aes-256 |
| *p1_hash* | Phase 1 integrity, also used as the PRF | sha256, sha384 |
| *dh* | Phase 1 Diffie-Hellman group | 14, 19, 20 |
| *p1_life* | Phase 1 lifetime in seconds | 28800. Only set on the ASA, Azure fixes it at 28800 |
| *p2_encr* | Phase 2 encryption | aes-192, aes-256 |
| *p2_hash* | Phase 2 integrity | sha-256 |
| *pfs* | Phase 2 Perfect Forward Secrecy group | group14, group19, group20 |
| *sa_life* | Phase 2 lifetime in seconds | 27000 (Azure default) |
| *sa_size* | Phase 2 lifetime in kilobytes | 102400000 (Azure default) |

The values use ASA syntax, which is why *p1_hash* is `sha256` and *p2_hash* is `sha-256`. The role converts them to the Azure names.

### Running the playbook

Run the playbook with one of these tags. A run with no tags (or `--tags all`) only deploys.

`uv run ansible-playbook playbook_cloud_vpn.yml --tags xxx`

- **`deploy`** Creates or updates everything. Safe to re-run, as everything already in place is left as it is.
  - AZ: *resource group, virtual network, subnets, GatewaySubnet, public IP, VPN gateway, local network gateway, VPN connection, IPsec policy, PSK*
  - ASA: *object-groups, crypto ikev2 enable, IKEv2 policy, IPsec proposal, IPsec profile, Tunnel1, static routes, tunnel ACL and its access-group, tunnel-group, sysopt connection tcpmss*

- **`destroy`** Removes everything for this VPN, except the shared parts listed under *Keeps*.
  - AZ: *VPN connection (and its IPsec policy), VPN gateway, public IP, local network gateway*
  - ASA: *Tunnel1 (its static routes go with it), IPsec profile, IPsec proposal, IKEv2 policy, tunnel-group, tunnel ACL and its access-group, object-groups*
  - Keeps: AZ *resource group, virtual network, subnets*. ASA *crypto ikev2 enable, sysopt connection tcpmss*

- **`vpn_down`** Deletes what breaks the VPN, which is also what Azure bills for. This includes the public IP, so the next *vpn_up* gets a new Azure IP.
  - AZ: *VPN connection, VPN gateway, public IP*
  - ASA: *tunnel destination, tunnel-group*

- **`vpn_up`** Brings the tunnel back up after *vpn_down*. It also updates the local network gateway in case the ASA's public IP has changed.
  - AZ: *public IP (new address), VPN gateway, local network gateway, VPN connection, IPsec policy, PSK*
  - ASA: *re-applies the whole config, which adds the tunnel destination and tunnel-group with the new Azure IP*

**Changing settings by re-running `deploy`**
- **PSK:** updated on both ends.
- **Crypto variables:** the Azure IPsec policy is replaced first, so the tunnel drops until the ASA play updates the ASA to match.
- **Adding subnets or address spaces:** works on both ends.

#### Known limitations

- **Removing subnets or address spaces doesn't remove them.** The ASA template only adds lines, so a removed *network-object* or static route stays on the ASA. The virtual network task doesn't purge, so a removed address space stays in Azure. Remove them by hand.
- **Changing *p2_encr* leaves the old IPsec proposal and profile on the ASA.** Their names include it (*AZ_ESP_AES256*), so new ones are made. A later *destroy* only looks for the current name, so remove the old ones by hand.
- **`--check` on a brand-new deploy fails at the IPsec policy step**, as the VPN connection doesn't exist yet. Check mode works once the VPN has been deployed.

#### Setting the public IPs yourself

The dynamic public IP lookup can be overridden by manually setting `rmte_public_ip` or `cld_public_ip` in *group_vars/all.yml* or with `-e`. Use it when:

- The Ansible host isn't behind the ASA (`rmte_public_ip`)
- Running only the ASA part (`cld_public_ip`)
- Azure is gone but the ASA still needs cleaning up (`cld_public_ip`). Use the old Azure IP so `destroy` finds the tunnel-group

If the ASA public IP changes, nothing needs setting. Re-run `deploy` or `vpn_up` and the local network gateway is updated with the new IP.

```bash
# Get the current Azure IP (to use as cld_public_ip)
az network public-ip show -g <az_rg_name> -n <az_public_ip_name> --query ipAddress -o tsv
# Ansible host isn't behind the ASA (ASA public IP)
uv run ansible-playbook playbook_cloud_vpn.yml --tags deploy -e rmte_public_ip=x.x.x.x
# Only the ASA part (current Azure IP)
uv run ansible-playbook playbook_cloud_vpn.yml --tags deploy --limit asa -e cld_public_ip=x.x.x.x
# Azure is gone, clean up the ASA (old Azure IP)
uv run ansible-playbook playbook_cloud_vpn.yml --tags destroy --limit asa -e cld_public_ip=x.x.x.x
```

### Upgrading the Azure collection

*azure.azcollection* pins every Azure SDK package to an exact version in its own *requirements.txt*. The modules only work with that set, so the collection and the SDK must be upgraded together.

Check the SDK matches the collection: *Would make no changes* means they match. Anything else lists the packages that are out of sync.\
`uv pip install --dry-run -r collections/ansible_collections/azure/azcollection/requirements.txt`

**Upgrade**
1. Change the *azure.azcollection* version in *collections/requirements.yml*, for example `"==4.3.0"`
2. Install it with `uv run ansible-galaxy collection install -r collections/requirements.yml --upgrade`
3. Sync the SDK packages to the new collection's list with `uv add -r collections/ansible_collections/azure/azcollection/requirements.txt`
4. Run the check above. It must say *Would make no changes*
5. Run `uv run ansible-lint` and `uv run ansible-playbook playbook_cloud_vpn.yml --syntax-check`
6. Run `--check --diff` against a test subscription, then update the version under [Versions](#versions)
7. Commit *collections/requirements.yml*, *pyproject.toml* and *uv.lock* together

If `uv add` fails on a pre-release dependency, add that package with an exact pin, for example `uv add "msal==1.33.0b1"` (needed for 4.1.0). Remove the pin again once a later collection no longer needs it.
