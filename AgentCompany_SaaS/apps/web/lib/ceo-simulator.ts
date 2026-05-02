export function createCeoReply(userMessage: string) {
  const cleanMessage = userMessage.trim();

  if (!cleanMessage) {
    return "I need a clear goal before I can build a useful plan.";
  }

  return [
    "Understood. I will treat this as a product request and keep it tied to the current tenant and project.",
    "",
    `Request: "${cleanMessage}"`,
    "",
    "Next I would break this into a CEO plan, manager tasks, worker tasks, required tools, and approval points. The real model runtime is not connected yet, so this is the structured placeholder response."
  ].join("\n");
}
