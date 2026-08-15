import assert from "node:assert/strict";
import test from "node:test";

import {
  LatestOnlyGate,
  buildExactPreviewPrompt,
} from "../../web/exact_preview_prompt.js";

test("exact preview prompt keeps only the processor ancestor graph", () => {
  const graph = {
    "10": { class_type: "LoadImage", inputs: { image: "portrait.png" } },
    "11": { class_type: "SkinBeautySettingsCN", inputs: { preset: "关闭" } },
    "12": { class_type: "SolidMask", inputs: { value: 1 } },
    "20": {
      class_type: "SkinBeautyProcessorCN",
      inputs: {
        图像: ["10", 0],
        美白参数: ["11", 0],
        外部遮罩: ["12", 0],
        生成节点预览: true,
      },
    },
    "186": { class_type: "VideoCombine", inputs: { images: ["20", 0] } },
    "187": { class_type: "SaveVideo", inputs: { video: ["186", 0] } },
    "999": { class_type: "UnrelatedOutput", inputs: {} },
  };

  const prompt = buildExactPreviewPrompt(
    graph,
    "20",
    "skinbeauty_exact_request",
    "request",
    "SkinBeautyPreviewSinkCN",
  );

  assert.deepEqual(Object.keys(prompt).sort(), ["10", "11", "12", "20", "skinbeauty_exact_request"]);
  assert.equal(prompt["20"].inputs.生成节点预览, false);
  assert.deepEqual(prompt.skinbeauty_exact_request.inputs.before, ["10", 0]);
  assert.deepEqual(prompt.skinbeauty_exact_request.inputs.after, ["20", 0]);
  assert.equal(prompt.skinbeauty_exact_request.class_type, "SkinBeautyPreviewSinkCN");
  assert.equal(graph["20"].inputs.生成节点预览, true, "source prompt must not be mutated");
  assert.equal(prompt["186"], undefined);
  assert.equal(prompt["187"], undefined);
  assert.equal(prompt["999"], undefined);
});

test("single-flight gate drops intermediate requests and never overlaps", async () => {
  const gate = new LatestOnlyGate();
  const started = [];
  let active = 0;
  let maximumActive = 0;
  let releaseFirst;
  const firstBlocked = new Promise((resolve) => { releaseFirst = resolve; });

  const task = async (token) => {
    started.push(token);
    active += 1;
    maximumActive = Math.max(maximumActive, active);
    if (token === 1) await firstBlocked;
    active -= 1;
    return token;
  };

  const first = gate.request(1, task);
  await Promise.resolve();
  const second = gate.request(2, task);
  const third = gate.request(3, task);
  releaseFirst();

  assert.equal(await second, false);
  assert.equal(await third, false);
  assert.equal(await first, 3);
  assert.deepEqual(started, [1, 3]);
  assert.equal(maximumActive, 1);
});
