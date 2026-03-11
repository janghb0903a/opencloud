# Monthly Infra Check (Ansible)

This project runs monthly checks on OpenStack and Kubernetes hosts from a bastion server and writes one output file per host.

## Output Rules

- Output directory: `/tmp/check_YYMMDD`
- Output file: `{{ inventory_hostname }}_check` (no extension)
- Example: `/tmp/check_260227/ctrl01_check`

## Project Layout

```text
ansible-monthly-check/
|- ansible.cfg
|- inventories/prod/hosts.ini.sample
|- group_vars/all.yml
|- playbooks/monthly_check.yml
`- roles/monthly_check/
   |- tasks/main.yml
   |- templates/host_report.md.j2
   `- vars/check_items.yml
```

## Inventory Groups (expected)

Use these group names in your real inventory (`inventories/prod/hosts.ini`):

- `openstack-compute`
- `openstack-control`
- `openstack-control-01`
- `kubernetes-master`
- `kubernetes-worker`
- `kubernetes-master-01`

You can import actual hosts later.

## Run

```bash
cd ansible-monthly-check
ansible-playbook -i inventories/prod/hosts.ini playbooks/monthly_check.yml
# or
bash ./run_monthly_check.sh inventories/prod/hosts.ini
```

## Targeting Rules

- `targets`: run on listed groups.
- `primary_of`: run only on hosts that belong to this dedicated singleton group (for example `openstack-control-01`, `kubernetes-master-01`).
- `hosts`: run only on listed hostnames.

If a check does not match the current host, report output shows `[SKIPPED]`.

