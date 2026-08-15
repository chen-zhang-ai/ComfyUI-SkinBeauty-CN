import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { LatestOnlyGate, buildExactPreviewPrompt } from "./exact_preview_prompt.js";

const SETTINGS_CLASS = "SkinBeautySettingsCN";
const PROCESSOR_CLASS = "SkinBeautyProcessorCN";
const PREVIEW_SINK_CLASS = "SkinBeautyPreviewSinkCN";
const exactRequests = new Map();
// Some third-party on-prompt hooks require the canonical workflow keys even
// when a partial execution intentionally omits all user workflow metadata.
// Return a fresh mutable object because those hooks may append transient maps.
function emptyPreviewWorkflow() {
  return { nodes: [], links: [] };
}

const TEXT = {
  en: {
    waiting: "Waiting for a source image…",
    connectSource: "Connect a source image and settings node",
    compareHint: "Connect a source image to compare before and after",
    before: "Before",
    after: "After",
    refreshExact: "Original-resolution exact preview (no video run)",
    exactProcessing: "Processing exact preview…",
    exactComplete: "Exact preview ready (same source as final processing)",
    displayOnly: "Display scaling only; final IMAGE is unchanged",
    exactFailed: "Exact preview failed",
    parametersUpdated: "Parameters changed; waiting for exact preview…",
    clickPreview: "Parameters changed; click exact preview",
    modeUpdated: "Mode changed; click exact preview",
    nodeComplete: "Node processing complete",
    imageLoadFailed: "Reference image failed to load",
    resultLoadFailed: "Node result preview failed to load",
    modelReady: "MediaPipe semantic model ready",
    modelFallback: "Using the pure algorithm fallback",
    modelDownloadOnly: "MediaPipe: allow model download only; never installs Python packages",
  },
  zh: {
    waiting: "等待参考图…",
    connectSource: "请连接参考图和参数面板",
    compareHint: "连接参考图后显示美白前后对比",
    before: "原图",
    after: "结果",
    refreshExact: "原分辨率精确预览（不跑视频）",
    exactProcessing: "精确预览处理中…",
    exactComplete: "精确预览完成（与正式处理同源）",
    displayOnly: "仅显示缩放，不影响正式输出",
    exactFailed: "精确预览失败",
    parametersUpdated: "参数已更新，等待精确预览…",
    clickPreview: "参数已更新，点击精确预览",
    modeUpdated: "模式已更新，点击精确预览",
    nodeComplete: "节点处理完成",
    imageLoadFailed: "参考图加载失败",
    resultLoadFailed: "节点结果预览加载失败",
    modelReady: "MediaPipe 语义模型已就绪",
    modelFallback: "正在使用纯算法安全回退",
    modelDownloadOnly: "MediaPipe：仅允许下载模型，不安装Python包",
  },
};

function currentLocale() {
  let value = "";
  try {
    value = app.extensionManager?.setting?.get?.("Comfy.Locale") || "";
  } catch (_) {
    // The public setting API may be unavailable on older ComfyUI builds.
  }
  if (!value) {
    try {
      value = app.ui?.settings?.getSettingValue?.("Comfy.Locale") || "";
    } catch (_) {
      // Continue through the documented DOM/browser fallbacks.
    }
  }
  if (!value) value = document.documentElement?.lang || "";
  if (!value) value = navigator.language || "";
  const normalized = String(value).replace(/_/g, "-").toLowerCase();
  return ["zh", "zh-cn", "zh-hans"].includes(normalized) ? "zh" : "en";
}

function text(key) {
  const locale = currentLocale();
  return TEXT[locale]?.[key] ?? TEXT.en[key] ?? key;
}

function refreshLocaleText() {
  for (const node of app.graph?._nodes || []) {
    if (node.comfyClass === PROCESSOR_CLASS || node.type === PROCESSOR_CLASS) {
      node.setDirtyCanvas(true, true);
    }
  }
}

const PRESETS = {
  "关闭": [0, 0, 0, 0, 0, 0, 80, 0, 0, 100, 58, 12],
  "低档·自然提亮": [48, 34, 20, 5, 16, 10, 78, -4, 6, 94, 56, 10],
  "中档·自然冷白": [72, 52, 42, 8, 28, 18, 72, -8, 12, 88, 58, 12],
  "高档·通透冷白": [88, 70, 62, 10, 42, 28, 66, -13, 20, 82, 60, 14],
  "冷白皮": [82, 62, 68, 4, 34, 20, 74, -12, 10, 91, 58, 12],
  "粉润白": [76, 56, 30, 28, 34, 18, 72, -4, 15, 86, 58, 12],
  "奶油白": [74, 60, 8, 12, 38, 24, 68, -10, 18, 84, 57, 13],
};

const SLIDER_NAMES = [
  "总强度", "美白", "冷暖", "红润", "匀肤", "暗部提亮",
  "高光保护", "饱和度", "平滑", "纹理保留", "肤色识别", "蒙版羽化",
];

function widget(node, name) {
  return node?.widgets?.find((item) => item.name === name);
}

function linkedInputNode(node, slot) {
  const linkId = node?.inputs?.[slot]?.link;
  if (linkId == null) return null;
  const link = app.graph?.links?.[linkId];
  return link ? app.graph.getNodeById(link.origin_id) : null;
}

function viewUrl(info) {
  const query = new URLSearchParams({
    filename: info.filename,
    subfolder: info.subfolder || "",
    type: info.type || "input",
    rand: String(Date.now()),
  });
  return api.apiURL(`/view?${query.toString()}`);
}

function linkedSettings(processor) {
  const candidate = linkedInputNode(processor, 1);
  return candidate?.comfyClass === SETTINGS_CLASS || candidate?.type === SETTINGS_CLASS ? candidate : null;
}

function loadImage(url) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error(text("imageLoadFailed")));
    image.src = url;
  });
}

function displayCanvas(image, longest = 1600) {
  const scale = Math.min(1, longest / Math.max(image.naturalWidth, image.naturalHeight));
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(image.naturalWidth * scale));
  canvas.height = Math.max(1, Math.round(image.naturalHeight * scale));
  canvas.getContext("2d").drawImage(image, 0, 0, canvas.width, canvas.height);
  return canvas;
}

function roundedPath(ctx, x, y, width, height, radius) {
  ctx.beginPath();
  if (typeof ctx.roundRect === "function") ctx.roundRect(x, y, width, height, radius);
  else ctx.rect(x, y, width, height);
}

function ellipsizedText(ctx, value, maxWidth) {
  const text = String(value || "");
  if (ctx.measureText(text).width <= maxWidth) return text;
  const suffix = "…";
  let low = 0;
  let high = text.length;
  while (low < high) {
    const middle = Math.ceil((low + high) / 2);
    if (ctx.measureText(text.slice(0, middle) + suffix).width <= maxWidth) low = middle;
    else high = middle - 1;
  }
  return text.slice(0, low) + suffix;
}

function inside(bounds, pos) {
  return Boolean(bounds && pos && pos[0] >= bounds.x && pos[0] <= bounds.x + bounds.width
    && pos[1] >= bounds.y && pos[1] <= bounds.y + bounds.height);
}

function containedRect(image, bounds) {
  const imageWidth = image?.width || image?.naturalWidth || 1;
  const imageHeight = image?.height || image?.naturalHeight || 1;
  const ratio = Math.min(bounds.width / imageWidth, bounds.height / imageHeight);
  const width = imageWidth * ratio;
  const height = imageHeight * ratio;
  const x = bounds.x + (bounds.width - width) / 2;
  const y = bounds.y + (bounds.height - height) / 2;
  return { x, y, width, height };
}

function drawContained(ctx, image, rectangle) {
  ctx.drawImage(image, rectangle.x, rectangle.y, rectangle.width, rectangle.height);
}

function compareWidget() {
  return {
    name: "原图与美白结果对比",
    type: "SKIN_BEAUTY_COMPARE",
    serialize: false,
    computeSize(width) {
      // Like ComfyUI's image preview and rgthree's comparer, reserve only the
      // status row and use all remaining node height as a resizable viewport.
      return [width, 24];
    },
    draw(ctx, owner, width, y) {
      const state = owner._skinBeautyState || {};
      const padding = 8;
      const statusHeight = 22;
      const viewportY = y + statusHeight;
      const bounds = {
        x: padding,
        y: viewportY,
        width: Math.max(40, width - padding * 2),
        height: Math.max(1, Number(owner.size?.[1] || 0) - viewportY - 8),
      };
      state.compareBounds = bounds;

      ctx.save();
      ctx.font = "12px sans-serif";
      ctx.fillStyle = state.error ? "#ff9b9b" : "#c5d3dc";
      ctx.fillText(
        ellipsizedText(ctx, state.status || text(state.statusKey || "waiting"), width - padding * 2),
        padding,
        y + 15,
      );

      roundedPath(ctx, bounds.x, bounds.y, bounds.width, bounds.height, 8);
      ctx.fillStyle = "#070a0d";
      ctx.fill();
      ctx.save();
      roundedPath(ctx, bounds.x, bounds.y, bounds.width, bounds.height, 8);
      ctx.clip();

      const before = state.before;
      const after = state.exact;
      if (before && after) {
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = "high";
        const imageBounds = containedRect(before, bounds);
        state.imageBounds = imageBounds;
        const split = Math.max(0.005, Math.min(0.995, Number(state.split ?? 0.5)));
        const splitX = imageBounds.x + imageBounds.width * split;

        // Result below, original clipped above it. Both use the exact same
        // destination rectangle so portrait and landscape images stay aligned.
        drawContained(ctx, after, imageBounds);
        ctx.save();
        ctx.beginPath();
        ctx.rect(imageBounds.x, imageBounds.y, splitX - imageBounds.x, imageBounds.height);
        ctx.clip();
        drawContained(ctx, before, imageBounds);
        ctx.restore();

        // rgthree-style separator: a single unobtrusive line, without labels
        // or a large handle that covers the face.
        const previousComposite = ctx.globalCompositeOperation;
        ctx.globalCompositeOperation = "difference";
        ctx.strokeStyle = "rgba(255,255,255,.92)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(splitX + 0.5, imageBounds.y);
        ctx.lineTo(splitX + 0.5, imageBounds.y + imageBounds.height);
        ctx.stroke();
        ctx.globalCompositeOperation = previousComposite;
      } else {
        state.imageBounds = null;
        ctx.fillStyle = "#7d8c95";
        ctx.font = "13px sans-serif";
        ctx.textAlign = "center";
        ctx.fillText(text("compareHint"), bounds.x + bounds.width / 2, bounds.y + bounds.height / 2);
        ctx.textAlign = "left";
      }
      ctx.restore();
      roundedPath(ctx, bounds.x, bounds.y, bounds.width, bounds.height, 8);
      ctx.strokeStyle = state.compareHover ? "#5cb8cf" : "#344750";
      ctx.lineWidth = 1;
      ctx.stroke();
      ctx.restore();
    },
    mouse(event, pos, owner) {
      const state = owner._skinBeautyState || {};
      const bounds = state.imageBounds || state.compareBounds;
      const type = event?.type || "";
      const isInside = inside(bounds, pos);
      const updateSplit = () => {
        if (!bounds) return;
        state.split = Math.max(0.005, Math.min(0.995, (pos[0] - bounds.x) / bounds.width));
      };
      if ((type === "pointerdown" || type === "mousedown") && isInside && state.before && state.exact) {
        state.compareDragging = true;
        state.compareHover = true;
        updateSplit();
        owner.setDirtyCanvas(true, true);
        return true;
      }
      if (type === "pointermove" || type === "mousemove") {
        state.compareHover = isInside || Boolean(state.compareDragging);
        // Match rgthree's slide mode: hovering moves the fine separator;
        // holding the pointer works as a conventional drag as well.
        if (isInside || state.compareDragging) updateSplit();
        if (app.canvas?.canvas) app.canvas.canvas.style.cursor = isInside ? "col-resize" : "";
        owner.setDirtyCanvas(true, true);
        return Boolean(state.compareDragging);
      }
      if (type === "pointerup" || type === "mouseup" || type === "pointercancel") {
        const wasDragging = Boolean(state.compareDragging);
        state.compareDragging = false;
        state.compareHover = isInside;
        owner.setDirtyCanvas(true, true);
        return wasDragging;
      }
      if (type === "pointerleave" || type === "mouseleave") {
        state.compareHover = false;
        state.compareDragging = false;
        if (app.canvas?.canvas) app.canvas.canvas.style.cursor = "";
        owner.setDirtyCanvas(true, true);
      }
      return false;
    },
  };
}

function updateCompareFromNodePosition(node, pos) {
  const state = node?._skinBeautyState;
  if (!state) return false;
  const bounds = state?.imageBounds;
  const active = Boolean(state?.before && state?.exact && (inside(bounds, pos) || state.compareDragging));
  state.compareHover = active;
  if (active) {
    state.split = Math.max(0.005, Math.min(0.995, (pos[0] - bounds.x) / bounds.width));
  }
  if (app.canvas?.canvas) app.canvas.canvas.style.cursor = active ? "col-resize" : "";
  node?.setDirtyCanvas(true, true);
  return active;
}

function beginCompareFromNodePosition(node, pos) {
  const state = node?._skinBeautyState;
  if (!state?.before || !state?.exact || !inside(state.imageBounds, pos)) return false;
  state.compareDragging = true;
  updateCompareFromNodePosition(node, pos);
  return true;
}

function endCompareFromNodePosition(node, pos) {
  const state = node?._skinBeautyState;
  if (!state?.compareDragging) return false;
  updateCompareFromNodePosition(node, pos);
  state.compareDragging = false;
  state.compareHover = inside(state.imageBounds, pos);
  node.setDirtyCanvas(true, true);
  return true;
}

async function runAction(node, key, action) {
  const state = node._skinBeautyState;
  const button = state.buttons[key];
  if (button.busy) return;
  button.busy = true;
  button.pressed = false;
  button.flash = null;
  node.setDirtyCanvas(true, true);
  const ok = await action(node);
  button.busy = false;
  button.flash = ok ? "success" : "error";
  button.flashUntil = performance.now() + 1100;
  node.setDirtyCanvas(true, true);
  setTimeout(() => node.setDirtyCanvas(true, true), 1150);
}

function actionButton(key, labelKey, busyLabelKey, action) {
  return {
    name: labelKey,
    type: "SKIN_BEAUTY_ACTION",
    serialize: false,
    computeSize(width) {
      return [width, 23];
    },
    draw(ctx, owner, width, y, height) {
      const state = owner._skinBeautyState;
      const button = state.buttons[key];
      if (button.flashUntil && performance.now() > button.flashUntil) button.flash = null;
      const bounds = { x: 8, y: y + 1, width: width - 16, height: Math.max(18, height - 2) };
      button.bounds = bounds;
      let background = "#273840";
      let outline = "#4a626d";
      if (button.busy) {
        background = "#315c69";
        outline = "#70c3d8";
      } else if (button.pressed) {
        background = "#19313a";
        outline = "#8ee8ff";
      } else if (button.hover) {
        background = "#3b5661";
        outline = "#78c9dd";
      } else if (button.flash === "success") {
        background = "#285843";
        outline = "#70d6a0";
      } else if (button.flash === "error") {
        background = "#62383b";
        outline = "#ef999f";
      }
      ctx.save();
      roundedPath(ctx, bounds.x, bounds.y + (button.pressed ? 1 : 0), bounds.width, bounds.height - (button.pressed ? 1 : 0), 6);
      ctx.fillStyle = background;
      ctx.fill();
      ctx.strokeStyle = outline;
      ctx.lineWidth = button.hover || button.pressed ? 1.5 : 1;
      ctx.stroke();
      ctx.fillStyle = "#f2f7f9";
      ctx.font = "600 12px sans-serif";
      ctx.textAlign = "center";
      const label = text(labelKey);
      const buttonText = button.busy ? text(busyLabelKey) : button.flash === "success" ? `${label}  ✓` : label;
      ctx.fillText(buttonText, bounds.x + bounds.width / 2, bounds.y + bounds.height / 2 + 4 + (button.pressed ? 1 : 0));
      ctx.textAlign = "left";
      ctx.restore();
    },
    mouse(event, pos, owner) {
      const button = owner._skinBeautyState.buttons[key];
      const type = event?.type || "";
      const isInside = inside(button.bounds, pos);
      if (type === "pointermove" || type === "mousemove") {
        button.hover = isInside;
        owner.setDirtyCanvas(true, true);
        return false;
      }
      if ((type === "pointerdown" || type === "mousedown") && isInside && !button.busy) {
        if (button.pressed) return true;
        button.pressed = true;
        button.hover = true;
        owner.setDirtyCanvas(true, true);
        setTimeout(() => runAction(owner, key, action), 70);
        return true;
      }
      if (type === "pointerup" || type === "mouseup" || type === "pointercancel") {
        const wasPressed = Boolean(button.pressed);
        button.pressed = false;
        button.hover = isInside;
        owner.setDirtyCanvas(true, true);
        return wasPressed;
      }
      if (type === "pointerleave" || type === "mouseleave") {
        button.hover = false;
        button.pressed = false;
        owner.setDirtyCanvas(true, true);
      }
      return false;
    },
  };
}

function safeNodeId(value) {
  return String(value).replace(/[^0-9A-Za-z_-]+/g, "_").slice(0, 48) || "node";
}

function exactRequestPromise(targetId, node) {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      exactRequests.delete(targetId);
      reject(new Error("Exact preview timed out"));
    }, 10 * 60 * 1000);
    exactRequests.set(targetId, { node, promptId: null, resolve, reject, timeout });
  });
}

function finishExactRequest(targetId, callback) {
  const pending = exactRequests.get(String(targetId));
  if (!pending) return false;
  exactRequests.delete(String(targetId));
  clearTimeout(pending.timeout);
  callback(pending);
  return true;
}

function onExactExecuted(event) {
  const detail = event?.detail || {};
  finishExactRequest(detail.node, (pending) => pending.resolve(detail.output || {}));
}

function onExactExecutionFailed(event) {
  const detail = event?.detail || {};
  for (const [targetId, pending] of exactRequests) {
    if (pending.promptId && pending.promptId === detail.prompt_id) {
      // Server exception text can contain implementation details or local
      // paths. Keep the browser-facing failure intentionally generic.
      finishExactRequest(targetId, (entry) => entry.reject(new Error(text("exactFailed"))));
    }
  }
}

function cancelExactRequests(node) {
  for (const [targetId, pending] of exactRequests) {
    if (pending.node === node) {
      finishExactRequest(targetId, (entry) => entry.reject(new Error("Exact preview node was removed")));
    }
  }
}

async function queueExactPrompt(node, token) {
  const graphPrompt = await app.graphToPrompt();
  const processorId = String(node.id);
  const requestId = `${safeNodeId(node.id)}_${token}_${Date.now()}`;
  const targetId = `skinbeauty_exact_${requestId}`;
  // The builder clones only the processor and its IMAGE/settings/MASK
  // ancestors, then injects one dev-only partial-execution output target.
  const output = buildExactPreviewPrompt(
    graphPrompt.output,
    processorId,
    targetId,
    requestId,
    PREVIEW_SINK_CLASS,
  );

  const resultPromise = exactRequestPromise(targetId, node);
  try {
    const queued = await api.queuePrompt(
      0,
      { output, workflow: emptyPreviewWorkflow() },
      { partialExecutionTargets: [targetId] },
    );
    const pending = exactRequests.get(targetId);
    if (pending) pending.promptId = queued.prompt_id;
  } catch (error) {
    finishExactRequest(targetId, (pending) => pending.reject(error));
  }
  return resultPromise;
}

async function applyPreviewPayload(node, payload, token, statusKey) {
  const beforeInfo = payload?.skin_beauty_before?.[0];
  const afterInfo = payload?.skin_beauty_preview?.[0];
  if (!beforeInfo || !afterInfo) throw new Error(text("resultLoadFailed"));
  const [before, after] = await Promise.all([
    loadImage(viewUrl(beforeInfo)),
    loadImage(viewUrl(afterInfo)),
  ]);
  const state = node._skinBeautyState;
  if (token != null && token !== state.exactToken) return false;
  state.before = displayCanvas(before);
  state.exact = displayCanvas(after);
  state.status = statusKey === "exactComplete" ? `${text(statusKey)} · ${text("displayOnly")}` : "";
  state.statusKey = statusKey;
  state.statusDetail = text("displayOnly");
  state.error = false;
  node.setDirtyCanvas(true, true);
  return true;
}

async function executeExactNow(node, token) {
  const state = node._skinBeautyState;
  if (token !== state.exactToken) return false;
  state.exactInFlight = true;
  state.status = "";
  state.statusKey = "exactProcessing";
  state.error = false;
  node.setDirtyCanvas(true, true);
  let ok = false;
  try {
    const payload = await queueExactPrompt(node, token);
    ok = await applyPreviewPayload(node, payload, token, "exactComplete");
  } catch (error) {
    if (token === state.exactToken) {
      console.warn(`[SkinBeauty-CN] ${text("exactFailed")}`, error);
      state.status = "";
      state.statusKey = "exactFailed";
      state.error = true;
      node.setDirtyCanvas(true, true);
    }
  } finally {
    state.exactInFlight = false;
  }
  return ok;
}

async function executeExact(node, token) {
  const state = node._skinBeautyState;
  if (token !== state.exactToken) return false;
  return state.exactGate.request(token, (latestToken) => executeExactNow(node, latestToken));
}

async function refreshExact(node) {
  clearTimeout(node._skinBeautyExactTimer);
  const token = ++node._skinBeautyState.exactToken;
  return executeExact(node, token);
}

function scheduleExact(node, delay = 0) {
  clearTimeout(node._skinBeautyExactTimer);
  const state = node._skinBeautyState;
  // Invalidate an older in-flight result as soon as a parameter changes, not
  // only when the next request starts.
  const scheduledToken = ++state.exactToken;
  if (delay > 0) {
    state.status = "";
    state.statusKey = "parametersUpdated";
    state.error = false;
    node.setDirtyCanvas(true, true);
  }
  node._skinBeautyExactTimer = setTimeout(() => {
    if (state.exactToken === scheduledToken) executeExact(node, scheduledToken);
  }, delay);
}

function refreshLinkedProcessors(settings) {
  for (const node of app.graph?._nodes || []) {
    if ((node.comfyClass === PROCESSOR_CLASS || node.type === PROCESSOR_CLASS) && linkedSettings(node)?.id === settings.id) {
      if (node._skinBeautyAutoExact) {
        scheduleExact(node, 650);
      } else {
        node._skinBeautyState.status = "";
        node._skinBeautyState.statusKey = "clickPreview";
        node.setDirtyCanvas(true, true);
      }
    }
  }
}

function installSettings(node) {
  if (node._skinBeautyInstalled) return;
  node._skinBeautyInstalled = true;
  node.color = "#74546d";
  node.bgcolor = "#2a2029";
  let applyingPreset = false;
  const presetWidget = widget(node, "预设");
  if (presetWidget) {
    const original = presetWidget.callback;
    presetWidget.callback = function (value, ...args) {
      original?.call(this, value, ...args);
      const values = PRESETS[value];
      if (values) {
        applyingPreset = true;
        SLIDER_NAMES.forEach((name, index) => {
          const target = widget(node, name);
          if (target) target.value = values[index];
        });
        applyingPreset = false;
      }
      refreshLinkedProcessors(node);
      node.setDirtyCanvas(true, true);
    };
  }
  for (const name of SLIDER_NAMES) {
    const slider = widget(node, name);
    if (!slider) continue;
    const original = slider.callback;
    slider.callback = function (value, ...args) {
      original?.call(this, value, ...args);
      if (!applyingPreset && presetWidget && presetWidget.value !== "自定义") presetWidget.value = "自定义";
      refreshLinkedProcessors(node);
    };
  }
}

function installProcessor(node) {
  if (node._skinBeautyInstalled) return;
  node._skinBeautyInstalled = true;
  node.color = "#376574";
  node.bgcolor = "#17262d";
  node._skinBeautyState = {
    status: "",
    statusKey: "waiting",
    statusDetail: "",
    exactToken: 0,
    exactInFlight: false,
    exactGate: new LatestOnlyGate(),
    error: false,
    split: 0.5,
    compareHover: false,
    compareDragging: false,
    buttons: {
      exact: { hover: false, pressed: false, busy: false, flash: null, flashUntil: 0 },
    },
  };
  // Avoid ComfyUI's standard gallery below the node. The execution thumbnail
  // is consumed by our comparer through the private UI payload instead.
  node.imgs = [];
  node.preview = null;
  if (typeof node.addCustomWidget === "function") {
    node.addCustomWidget(actionButton(
      "exact",
      "refreshExact",
      "exactProcessing",
      refreshExact,
    ));
    node.addCustomWidget(compareWidget());
  }
  const autoWidget = widget(node, "实时精确预览");
  node._skinBeautyAutoExact = Boolean(autoWidget?.value);
  if (autoWidget) {
    const originalAuto = autoWidget.callback;
    autoWidget.callback = function (value, ...args) {
      originalAuto?.call(this, value, ...args);
      node._skinBeautyAutoExact = Boolean(value);
      if (node._skinBeautyAutoExact) scheduleExact(node, 0);
    };
  }
  for (const name of ["蒙版模式", "语义蒙版", "批处理", "计算设备"]) {
    const modeWidget = widget(node, name);
    if (!modeWidget) continue;
    const originalMode = modeWidget.callback;
    modeWidget.callback = function (value, ...args) {
      originalMode?.call(this, value, ...args);
      if (node._skinBeautyAutoExact) scheduleExact(node, 650);
      else {
        node._skinBeautyState.status = "";
        node._skinBeautyState.statusKey = "modeUpdated";
        node.setDirtyCanvas(true, true);
      }
    };
  }
  const originalConnectionsChange = node.onConnectionsChange;
  node.onConnectionsChange = function (...args) {
    originalConnectionsChange?.apply(this, args);
    this._skinBeautyState.before = null;
    this._skinBeautyState.exact = null;
    if (this._skinBeautyAutoExact) scheduleExact(this, 650);
  };
  // Current ComfyUI does not continuously forward hover movement to a custom
  // widget's mouse() callback. rgthree tracks it at node level, so do the same.
  const originalMouseDown = node.onMouseDown;
  node.onMouseDown = function (event, pos, canvas) {
    if (beginCompareFromNodePosition(this, pos)) return true;
    return originalMouseDown?.call(this, event, pos, canvas);
  };
  const originalMouseMove = node.onMouseMove;
  node.onMouseMove = function (event, pos, canvas) {
    originalMouseMove?.call(this, event, pos, canvas);
    updateCompareFromNodePosition(this, pos);
  };
  const originalMouseUp = node.onMouseUp;
  node.onMouseUp = function (event, pos, canvas) {
    if (endCompareFromNodePosition(this, pos)) return true;
    return originalMouseUp?.call(this, event, pos, canvas);
  };
  const originalMouseLeave = node.onMouseLeave;
  node.onMouseLeave = function (event) {
    originalMouseLeave?.call(this, event);
    this._skinBeautyState.compareHover = false;
    this._skinBeautyState.compareDragging = false;
    if (app.canvas?.canvas) app.canvas.canvas.style.cursor = "";
    this.setDirtyCanvas(true, true);
  };
  const originalExecuted = node.onExecuted;
  node.onExecuted = function (message) {
    originalExecuted?.call(this, message);
    this.imgs = [];
    this.preview = null;
    applyPreviewPayload(this, message, null, "nodeComplete")
      .catch((error) => console.warn(`[SkinBeauty-CN] ${text("resultLoadFailed")}`, error));
  };
  const originalRemoved = node.onRemoved;
  node.onRemoved = function (...args) {
    clearTimeout(this._skinBeautyExactTimer);
    cancelExactRequests(this);
    originalRemoved?.apply(this, args);
  };
  setTimeout(() => {
    if (node._skinBeautyAutoExact) scheduleExact(node, 0);
  }, 450);
  node.setSize([Math.max(node.size[0], 520), Math.max(node.size[1], 900)]);
}

app.registerExtension({
  name: "ComfyUI.SkinBeautyCN",
  async setup() {
    app.ui?.settings?.addEventListener?.("Comfy.Locale.change", refreshLocaleText);
    api.addEventListener("executed", onExactExecuted);
    api.addEventListener("execution_error", onExactExecutionFailed);
    api.addEventListener("execution_interrupted", onExactExecutionFailed);
  },
  async nodeCreated(node) {
    if (node.comfyClass === SETTINGS_CLASS) installSettings(node);
    if (node.comfyClass === PROCESSOR_CLASS) installProcessor(node);
  },
});
