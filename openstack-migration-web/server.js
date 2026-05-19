const express = require("express");
const path = require("path");

const app = express();
const PORT = process.env.PORT || 8080;

app.use(express.json());
app.use(express.static(path.join(__dirname, "public")));

// Demo dataset for initial testing. Replace with live OpenStack discovery later.
const DEMO_INSTANCES = [
  {
    id: "inst-001",
    name: "test-os-data-01",
    volumes: [
      { id: "vol-a1", name: "test-os-data-01-root" },
      { id: "vol-a2", name: "test-os-data-01-data" }
    ]
  },
  {
    id: "inst-002",
    name: "test-os-data-02",
    volumes: [
      { id: "vol-b1", name: "test-os-data-02-root" }
    ]
  },
  {
    id: "inst-003",
    name: "infra-db-01",
    volumes: [
      { id: "vol-c1", name: "infra-db-01-root" },
      { id: "vol-c2", name: "infra-db-01-log" }
    ]
  }
];

app.get("/api/instances", (req, res) => {
  const q = (req.query.q || "").toLowerCase();
  const filtered = DEMO_INSTANCES.filter((item) => item.name.toLowerCase().includes(q));
  res.json({ items: filtered });
});

app.post("/api/workflow/plan", (req, res) => {
  const payload = req.body || {};
  const hostname = payload.hostname || "test-os-data-01";
  const selected = DEMO_INSTANCES.find((x) => x.name === hostname);
  const volumes = Array.isArray(payload.volumes) && payload.volumes.length > 0
    ? payload.volumes
    : selected
      ? selected.volumes
      : [];

  const plan = buildPlan({ hostname, volumes, networkPorts: payload.networkPorts || [] });
  res.json(plan);
});

function buildPlan({ hostname, volumes, networkPorts }) {
  const repVolumes = volumes.map((v) => ({
    originalId: v.id,
    originalName: v.name,
    repName: `${v.name}-rep`
  }));

  const step1 = repVolumes.map((v) =>
    `openstack volume create --source ${v.originalId} ${v.repName}`
  );

  const step2 = repVolumes.map((v) =>
    `cinder unmanage ${v.repName}`
  );

  const step3 = [
    "# source-id lookup idea",
    "# 1) Before unmanage: save OpenStack volume id/name mapping",
    "# 2) After unmanage: cinder manageable-list --host cinder-volume-worker@powerflex#PD-1:SP-1",
    "# 3) Match entries by safe marker (name or size), then use reference.source-id",
    ...repVolumes.map((v) =>
      `openstack volume create --remote-source source-id=<SOURCE_ID_FOR_${v.repName}> --host cinder-volume-worker@powerflex#PD-1:SP-1 --type powerflex ${v.repName}`
    )
  ];

  const step4 = repVolumes.flatMap((v) => [
    `openstack volume create --source <UUID_OF_${v.repName}> ${v.originalName}`,
    `openstack volume delete ${v.repName}`
  ]);

  const networkCmds = networkPorts.length > 0
    ? networkPorts.map((port, idx) =>
      `openstack port create --network ${port.network || "<NETWORK_ID>"} --fixed-ip subnet=${port.subnet || "<SUBNET_ID>"},ip-address=${port.ip || `<AUTO_${idx + 1}>`} ${hostname}-port-${idx + 1}`
    )
    : [`openstack port create --network <NETWORK_ID> ${hostname}-port-1`];

  const vmCmd = [
    `openstack server create --flavor <FLAVOR> --image <IMAGE_OR_BOOT_VOLUME> --nic port-id=<PORT_ID_1> ${hostname}`
  ];

  return {
    meta: {
      hostname,
      volumeCount: repVolumes.length,
      generatedAt: new Date().toISOString()
    },
    steps: [
      { key: "clone_old", title: "(Old) Clone Attached Volumes with -rep", commands: step1 },
      { key: "unmanage_old", title: "(Old) Unmanage -rep Volumes", commands: step2 },
      { key: "import_new", title: "(New) Re-create from PowerFlex source-id", commands: step3 },
      { key: "reclone_clean", title: "Clone Again and Remove -rep", commands: step4 },
      { key: "network", title: "Create Network Ports", commands: networkCmds },
      { key: "vm", title: "Create VM", commands: vmCmd }
    ]
  };
}

app.get("/healthz", (req, res) => {
  res.json({ ok: true });
});

app.listen(PORT, () => {
  console.log(`openstack-migration-web is running on port ${PORT}`);
});
