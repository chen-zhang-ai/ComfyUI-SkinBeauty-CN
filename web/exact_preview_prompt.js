export function collectAncestorPrompt(graphOutput, processorId) {
  const minimal = {};
  const visit = (value) => {
    const id = String(value);
    if (minimal[id]) return;
    const promptNode = graphOutput[id];
    if (!promptNode) throw new Error(`Missing prompt node ${id}`);
    minimal[id] = structuredClone(promptNode);
    for (const input of Object.values(promptNode.inputs || {})) {
      if (Array.isArray(input) && input.length === 2 && graphOutput[String(input[0])]) {
        visit(input[0]);
      }
    }
  };
  visit(processorId);
  return minimal;
}

export function buildExactPreviewPrompt(graphOutput, processorId, targetId, requestId, sinkClass) {
  const id = String(processorId);
  const output = collectAncestorPrompt(graphOutput, id);
  const processorPrompt = output[id];
  if (!processorPrompt?.inputs?.["图像"] || !processorPrompt?.inputs?.["美白参数"]) {
    throw new Error("Skin Beauty processor requires connected IMAGE and settings inputs");
  }

  processorPrompt.inputs["生成节点预览"] = false;
  output[targetId] = {
    class_type: sinkClass,
    inputs: {
      before: processorPrompt.inputs["图像"],
      after: [id, 0],
      request_id: requestId,
    },
    _meta: { title: "Skin Beauty exact preview" },
  };
  return output;
}

export class LatestOnlyGate {
  constructor() {
    this.running = false;
    this.pending = null;
  }

  async request(token, task) {
    if (this.running) {
      this.pending = { token, task };
      return false;
    }
    this.running = true;
    let current = { token, task };
    let result = false;
    try {
      while (current) {
        this.pending = null;
        result = await current.task(current.token);
        current = this.pending;
      }
      return result;
    } finally {
      this.running = false;
    }
  }
}
