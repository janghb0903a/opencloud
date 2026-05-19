const hostnameQuery = document.getElementById("hostnameQuery");
const searchBtn = document.getElementById("searchBtn");
const hostnameSelect = document.getElementById("hostnameSelect");
const volumeList = document.getElementById("volumeList");
const portsContainer = document.getElementById("portsContainer");
const addPortBtn = document.getElementById("addPortBtn");
const portRowTemplate = document.getElementById("portRowTemplate");
const generateBtn = document.getElementById("generateBtn");
const planContainer = document.getElementById("planContainer");
const stepBar = document.getElementById("stepBar");

let instances = [];
let selectedVolumes = [];

const steps = [
  "볼륨복제",
  "볼륨해제",
  "신규연결",
  "재복제",
  "네트워크",
  "VM생성"
];

function renderStepBar() {
  stepBar.innerHTML = "";
  steps.forEach((step, idx) => {
    const el = document.createElement("div");
    el.className = "step-pill";
    el.textContent = `${idx + 1}. ${step}`;
    stepBar.appendChild(el);
  });
}

function addPortRow(defaults = {}) {
  const row = portRowTemplate.content.firstElementChild.cloneNode(true);
  row.querySelector(".network").value = defaults.network || "";
  row.querySelector(".subnet").value = defaults.subnet || "";
  row.querySelector(".ip").value = defaults.ip || "";
  row.querySelector(".remove-port").addEventListener("click", () => {
    row.remove();
    if (portsContainer.children.length === 0) addPortRow();
  });
  portsContainer.appendChild(row);
}

function renderVolumeList(volumes) {
  volumeList.innerHTML = "";
  selectedVolumes = [];

  volumes.forEach((vol) => {
    const wrap = document.createElement("label");
    wrap.className = "check-item";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = true;

    const text = document.createElement("span");
    text.textContent = `${vol.name} (${vol.id})`;

    checkbox.addEventListener("change", () => {
      selectedVolumes = getCheckedVolumes(volumes);
    });

    wrap.appendChild(checkbox);
    wrap.appendChild(text);
    volumeList.appendChild(wrap);
  });

  selectedVolumes = getCheckedVolumes(volumes);
}

function getCheckedVolumes(volumes) {
  const checks = [...volumeList.querySelectorAll("input[type='checkbox']")];
  return volumes.filter((_, idx) => checks[idx] && checks[idx].checked);
}

async function searchInstances() {
  const q = encodeURIComponent(hostnameQuery.value.trim());
  const response = await fetch(`/api/instances?q=${q}`);
  const data = await response.json();
  instances = data.items || [];

  hostnameSelect.innerHTML = "";
  instances.forEach((item) => {
    const option = document.createElement("option");
    option.value = item.name;
    option.textContent = `${item.name} (${item.id})`;
    hostnameSelect.appendChild(option);
  });

  const selected = instances[0];
  if (selected) {
    renderVolumeList(selected.volumes || []);
  } else {
    volumeList.innerHTML = "<p class='muted'>검색 결과가 없습니다.</p>";
  }
}

hostnameSelect.addEventListener("change", () => {
  const picked = instances.find((x) => x.name === hostnameSelect.value);
  renderVolumeList(picked ? picked.volumes : []);
});

searchBtn.addEventListener("click", searchInstances);
addPortBtn.addEventListener("click", () => addPortRow());

generateBtn.addEventListener("click", async () => {
  const selected = instances.find((x) => x.name === hostnameSelect.value);
  const networkPorts = [...portsContainer.querySelectorAll(".port-row")].map((row) => ({
    network: row.querySelector(".network").value.trim(),
    subnet: row.querySelector(".subnet").value.trim(),
    ip: row.querySelector(".ip").value.trim()
  }));

  const body = {
    hostname: hostnameSelect.value || (selected ? selected.name : ""),
    volumes: selectedVolumes,
    oldAuth: document.getElementById("oldAuth").value,
    newAuth: document.getElementById("newAuth").value,
    networkPorts
  };

  const response = await fetch("/api/workflow/plan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  const plan = await response.json();

  renderPlan(plan);
});

function renderPlan(plan) {
  planContainer.innerHTML = "";

  (plan.steps || []).forEach((step, idx) => {
    const card = document.createElement("div");
    card.className = "plan-card";

    const title = document.createElement("h3");
    title.textContent = `${idx + 1}. ${step.title}`;
    card.appendChild(title);

    step.commands.forEach((cmd) => {
      const code = document.createElement("code");
      code.textContent = cmd;
      card.appendChild(code);
    });

    planContainer.appendChild(card);
  });
}

renderStepBar();
addPortRow();
searchInstances();
