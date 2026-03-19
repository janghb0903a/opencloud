const DATA = {
  dev: {
    label: "개발",
    envChar: "t",
    networkKind: "(SDN)개발)ACI",
    serviceSlb: ["16.120.4.0/24", "16.120.5.0/24", "16.120.6.0/24"],
    serviceNonSlb: ["16.120.1.0/24", "16.120.3.0/24"],
    db: ["16.120.120.0/24", "16.120.122.0/24", "16.120.123.0/24"],
    mft: ["16.120.248.0/24", "16.120.250.0/24", "16.120.251.0/24"],
    backup: ["16.120.128.0/24", "16.120.130.0/24", "16.120.131.0/24"]
  },
  prod: {
    label: "운영",
    envChar: "o",
    networkKind: "(SDN)내부망_ACI",
    serviceSlb: ["16.104.0.0/24", "16.104.1.0/24"],
    serviceNonSlb: ["16.104.41.0/24"],
    db: ["16.105.0.0/24", "16.105.2.0/24", "16.105.3.0/24"],
    mft: ["88.21.0.0/24", "88.21.42.0/24", "88.21.43.0/24"],
    backup: ["77.21.0.0/24", "77.21.2.0/24", "77.21.3.0/24"]
  }
};

const NEXT_STEPS_HTML = `
  <div class="flow-cards">
    <article class="step-card">
      <div class="step-card-head">
        <span class="step-badge">STEP 1</span>
        <h4>VM 생성 완료 후 접속 계정 생성</h4>
      </div>
      <p class="step-highlight">클라우드 포탈 작업 완료 후 신청 가능</p>
      <p>- 계정관리연동 배치 적용 이후 진행 가능합니다.</p>
      <div class="step-path"><code>정보보호포탈 - 계정신청 - UNIX/LINUX 계정</code></div>
      <p>- 그룹 생성 후 계정등록 신청</p>
    </article>

    <article class="step-card">
      <div class="step-card-head">
        <span class="step-badge">STEP 2</span>
        <h4>⚙️ 파일시스템 생성 요청 (IT서버팀)</h4>
      </div>
      <p>- 할당된 데이터 영역 볼륨을 대상으로 파일시스템 요청 진행</p>
      <p>- 1번 단계와 병행 가능</p>
    </article>

    <article class="step-card optional">
      <div class="step-card-head">
        <span class="step-badge">OPTION</span>
        <h4>(필요시) 네트워크 라우팅/통합 DNS 등록</h4>
      </div>
      <p>- 복수의 네트워크 인터페이스 사용 시 라우팅 작업이 필요할 수 있습니다.</p>
      <p>- 내부망 도메인 연동 시 통합 DNS 서버 등록이 필요할 수 있습니다.</p>
    </article>
  </div>
`;

const CONTACTS_HTML = `
  <section class="contact-section">
    <h4>기술 지원 담당자</h4>
    <div class="contact-grid">
      <article class="contact-card">
        <p class="team">AX클라우드팀</p>
        <p class="name">곽*진</p>
        <p class="title">과장</p>
      </article>
      <article class="contact-card">
        <p class="team">AX클라우드팀</p>
        <p class="name">김*현</p>
        <p class="title">과장보</p>
      </article>
      <article class="contact-card">
        <p class="team">AX클라우드팀</p>
        <p class="name">장*훈</p>
        <p class="title">계장</p>
      </article>
      <article class="contact-card">
        <p class="team">AX클라우드팀</p>
        <p class="name">김*인</p>
        <p class="title">계장</p>
      </article>
    </div>
  </section>
`;

const state = {
  env: "",
  selected: {
    serviceMode: "",
    serviceIp: "",
    db: "",
    mft: "",
    backup: ""
  },
  hostnames: [""]
};

const stepOrder = ["env", "ip", "hostname", "finish"];
const steps = {
  env: document.getElementById("step-env"),
  ip: document.getElementById("step-ip"),
  hostname: document.getElementById("step-hostname"),
  finish: document.getElementById("step-finish")
};

function updateHostnameVisual() {
  const el = document.getElementById("hostname-slot-env");
  if (!el) return;
  el.textContent = state.env ? DATA[state.env].envChar : "t";
}

function setStepper(activeStep) {
  const idx = stepOrder.indexOf(activeStep);
  Array.from(document.querySelectorAll(".step-pill")).forEach((pill, i) => {
    pill.classList.toggle("is-active", i <= idx);
  });
}

function showStep(name) {
  Object.values(steps).forEach((step) => step.classList.remove("active"));
  steps[name].classList.add("active");
  setStepper(name);
}

function fillSelect(selectEl, items, selected) {
  selectEl.innerHTML = [`<option value="">선택 안 함</option>`, ...items.map((v) => `<option value="${v}">${v}</option>`)].join("");
  selectEl.value = selected || "";
}

function renderServiceSelect() {
  const wrap = document.getElementById("service-select-wrap");
  const select = document.getElementById("service-select");
  const cfg = DATA[state.env];

  if (!state.selected.serviceMode) {
    wrap.classList.add("hidden");
    fillSelect(select, [], "");
    return;
  }

  const items = state.selected.serviceMode === "slb" ? cfg.serviceSlb : cfg.serviceNonSlb;
  wrap.classList.remove("hidden");
  fillSelect(select, items, state.selected.serviceIp);
}

function renderIpSection() {
  const cfg = DATA[state.env];
  document.getElementById("prod-warning").classList.toggle("hidden", state.env !== "prod");
  document.getElementById("network-kind").textContent = cfg.networkKind;
  fillSelect(document.getElementById("db-select"), cfg.db, state.selected.db);
  fillSelect(document.getElementById("mft-select"), cfg.mft, state.selected.mft);
  fillSelect(document.getElementById("backup-select"), cfg.backup, state.selected.backup);
  renderServiceSelect();
}

function collectSelection() {
  state.selected.serviceMode = (document.querySelector('input[name="service_mode"]:checked') || {}).value || "";
  state.selected.serviceIp = document.getElementById("service-select").value || "";
  state.selected.db = document.getElementById("db-select").value || "";
  state.selected.mft = document.getElementById("mft-select").value || "";
  state.selected.backup = document.getElementById("backup-select").value || "";
}

function validateIpSelection() {
  const errs = [];
  const hasAny = [state.selected.serviceIp, state.selected.db, state.selected.mft, state.selected.backup].some(Boolean);
  if (!hasAny) errs.push("최소 1개 네트워크에서 IP를 선택해 주세요.");
  if (state.selected.serviceMode && !state.selected.serviceIp) errs.push("서비스 모드를 선택했다면 서비스 C 클래스를 선택해 주세요.");
  if (!state.selected.serviceMode && state.selected.serviceIp) errs.push("서비스 IP를 선택하려면 먼저 SLB/non-SLB를 선택해 주세요.");
  if (state.env === "prod" && !state.selected.backup) errs.push("운영 환경은 Backup IP 선택이 필수입니다.");
  return errs;
}

function validateHostname(hostname, env) {
  const errors = [];
  const expectedEnvChar = DATA[env].envChar;
  if (hostname.length !== 12) errors.push("총 12자리여야 합니다.");
  if (!hostname.startsWith("nb")) errors.push("1~2번째는 nb 여야 합니다.");
  if (!/^[a-z]{4}$/.test(hostname.slice(2, 6))) errors.push("3~6번째는 소문자 알파벳 4자리 메타코드여야 합니다.");
  if (hostname.charAt(6) !== "k") errors.push("7번째는 k 여야 합니다.");
  if (hostname.charAt(7) !== expectedEnvChar) errors.push(`8번째는 ${DATA[env].label} 환경이므로 ${expectedEnvChar} 여야 합니다.`);
  if (!/^[a-z]{2}$/.test(hostname.slice(8, 10))) errors.push("9~10번째는 소문자 2자리 업무 약어여야 합니다.");
  if (!/^[0-9]{2}$/.test(hostname.slice(10, 12))) errors.push("11~12번째는 숫자 2자리여야 합니다.");
  return errors;
}

function renderHostnameInputs() {
  const root = document.getElementById("hostname-list");
  root.innerHTML = state.hostnames.map((value, idx) => `
    <div class="hostname-row" data-idx="${idx}">
      <div class="hostname-row-head">
        <span class="hostname-row-title">Hostname ${idx + 1}</span>
        ${idx > 0 ? '<button type="button" class="btn secondary btn-remove-hostname">삭제</button>' : ""}
      </div>
      <input class="input hostname-input" type="text" maxlength="12" value="${value}" placeholder="예: nbabcdktdb01" />
    </div>
  `).join("");
}

function collectHostnames() {
  state.hostnames = Array.from(document.querySelectorAll(".hostname-input")).map((el) => el.value.trim());
}

function renderHostnameErrors(errors) {
  document.getElementById("hostname-errors").innerHTML = errors.map((e) => `<li>${e}</li>`).join("");
}

function getEnvPortalUrl() {
  const cfg = window.APP_CONFIG || {};
  if (state.env === "dev" && cfg.CLOUD_PORTAL_URL_DEV) return cfg.CLOUD_PORTAL_URL_DEV;
  if (state.env === "prod" && cfg.CLOUD_PORTAL_URL_PROD) return cfg.CLOUD_PORTAL_URL_PROD;
  return cfg.CLOUD_PORTAL_URL || "#";
}

function renderSummary() {
  const ipRows = [];
  if (state.selected.serviceIp) ipRows.push(`<li>서비스 (${state.selected.serviceMode.toUpperCase()}): ${state.selected.serviceIp}</li>`);
  if (state.selected.db) ipRows.push(`<li>DB: ${state.selected.db}</li>`);
  if (state.selected.mft) ipRows.push(`<li>MFT: ${state.selected.mft}</li>`);
  if (state.selected.backup) ipRows.push(`<li>Backup: ${state.selected.backup}</li>`);

  document.getElementById("summary").innerHTML = `
    <article class="summary-card"><h4>환경</h4><p>${DATA[state.env].label}</p></article>
    <article class="summary-card"><h4>망구분</h4><p>${DATA[state.env].networkKind}</p></article>
    <article class="summary-card"><h4>선택 IP</h4><ul>${ipRows.join("")}</ul></article>
    <article class="summary-card"><h4>Hostname (${state.hostnames.length}개)</h4><ul>${state.hostnames.map((v) => `<li>${v}</li>`).join("")}</ul></article>
  `;
}

function setupPortalButton() {
  const url = getEnvPortalUrl();
  document.getElementById("portal-btn").href = url;
  document.getElementById("portal-warning").classList.toggle("hidden", url !== "#");
}

function openModal(title, bodyHtml) {
  document.getElementById("modal-title").textContent = title;
  document.getElementById("modal-body").innerHTML = bodyHtml;
  document.getElementById("modal").classList.remove("hidden");
  document.getElementById("modal-backdrop").classList.remove("hidden");
}

function closeModal() {
  document.getElementById("modal").classList.add("hidden");
  document.getElementById("modal-backdrop").classList.add("hidden");
}

document.querySelectorAll(".env-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    state.env = btn.dataset.env;
    state.selected = { serviceMode: "", serviceIp: "", db: "", mft: "", backup: "" };
    state.hostnames = [""];
    updateHostnameVisual();
    renderIpSection();
    showStep("ip");
  });
});

document.addEventListener("change", (e) => {
  if (e.target && e.target.name === "service_mode") {
    state.selected.serviceMode = e.target.value || "";
    state.selected.serviceIp = "";
    renderServiceSelect();
  }
});

document.addEventListener("click", (e) => {
  if (e.target && e.target.classList.contains("btn-remove-hostname")) {
    const row = e.target.closest(".hostname-row");
    const idx = Number(row.dataset.idx);
    state.hostnames.splice(idx, 1);
    renderHostnameInputs();
  }
});

document.getElementById("add-hostname").addEventListener("click", () => {
  collectHostnames();
  state.hostnames.push("");
  renderHostnameInputs();
});

document.getElementById("back-to-env").addEventListener("click", () => showStep("env"));
document.getElementById("back-to-ip").addEventListener("click", () => showStep("ip"));
document.getElementById("back-to-hostname").addEventListener("click", () => showStep("hostname"));

document.getElementById("to-hostname").addEventListener("click", () => {
  const ipError = document.getElementById("ip-error");
  ipError.classList.add("hidden");
  collectSelection();
  const errs = validateIpSelection();
  if (errs.length > 0) {
    ipError.textContent = errs.join(" ");
    ipError.classList.remove("hidden");
    return;
  }

  document.getElementById("hostname-env-hint").textContent = `현재 선택 환경: ${DATA[state.env].label} (8번째 문자: ${DATA[state.env].envChar})`;
  updateHostnameVisual();
  renderHostnameInputs();
  renderHostnameErrors([]);
  showStep("hostname");
});

document.getElementById("to-finish").addEventListener("click", () => {
  collectHostnames();
  const allErrors = [];
  state.hostnames.forEach((hostname, idx) => {
    if (!hostname) {
      allErrors.push(`Hostname ${idx + 1}: 값이 비어 있습니다.`);
      return;
    }
    validateHostname(hostname, state.env).forEach((msg) => allErrors.push(`Hostname ${idx + 1}: ${msg}`));
  });

  renderHostnameErrors(allErrors);
  if (allErrors.length > 0) return;

  renderSummary();
  setupPortalButton();
  showStep("finish");
});

document.getElementById("btn-next-steps").addEventListener("click", () => openModal("이후 단계 안내", NEXT_STEPS_HTML));
document.getElementById("btn-contacts").addEventListener("click", () => openModal("담당자 정보", CONTACTS_HTML));
document.getElementById("modal-close").addEventListener("click", closeModal);
document.getElementById("modal-backdrop").addEventListener("click", closeModal);

updateHostnameVisual();
