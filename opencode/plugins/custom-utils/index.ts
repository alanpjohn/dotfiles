import { tool } from "@opencode-ai/plugin/tool";
import type { PluginModule } from "@opencode-ai/plugin";
import { mkdir, unlink } from "node:fs/promises";
import { existsSync } from "node:fs";
import { homedir } from "node:os";
import { createHash } from "node:crypto";

function getPlanPath(context: { worktree: string; sessionID: string }): string {
  const worktreeHash = createHash("sha256")
    .update(context.worktree)
    .digest("hex")
    .slice(0, 8);
  const planDir = `${homedir()}/.config/opencode/plans`;
  return `${planDir}/${worktreeHash}-${context.sessionID}`;
}

export const CustomUtilsPlugin: PluginModule = {
  id: "custom-utils",
  server: async (ctx) => {
    return {
      tool: {
        plan_create: tool({
          description:
            "[custom-utils] Create a new plan for this session. The filename is automatically managed and not visible to you. Use this to save your plan content.",
          args: {
            content: tool.schema
              .string()
              .describe("Plan content in markdown format"),
          },
          async execute(args, context) {
            const planDir = `${homedir()}/.config/opencode/plans`;
            const planPath = getPlanPath(context);

            try {
              // Create directory if needed
              await mkdir(planDir, { recursive: true });

              // Write plan content
              await Bun.write(planPath, args.content);

              return "Plan created successfully.";
            } catch (error) {
              return `Error creating plan: ${error instanceof Error ? error.message : String(error)}`;
            }
          },
        }),

        plan_read: tool({
          description:
            "[custom-utils] Read the current session's plan. Returns the plan content or an error if no plan exists.",
          args: {},
          async execute(_args, context) {
            const planPath = getPlanPath(context);

            try {
              if (!existsSync(planPath)) {
                return "No plan found for this session. Use plan_create to create one.";
              }

              const content = await Bun.file(planPath).text();
              return content;
            } catch (error) {
              return `Error reading plan: ${error instanceof Error ? error.message : String(error)}`;
            }
          },
        }),

        plan_update: tool({
          description:
            "[custom-utils] Update a specific section of the plan by matching the section header. For full rewrites, use plan_delete + plan_create instead.",
          args: {
            section: tool.schema
              .string()
              .describe("Section header to update (e.g., 'Project Overview')"),
            content: tool.schema
              .string()
              .describe("New content for the section"),
          },
          async execute(args, context) {
            const planPath = getPlanPath(context);

            try {
              if (!existsSync(planPath)) {
                return "No plan found for this session. Use plan_create to create one.";
              }

              const planContent = await Bun.file(planPath).text();
              const lines = planContent.split("\n");

              // Find the section header
              const sectionRegex = /^(#{1,6})\s+(.+)$/;
              let sectionStart = -1;
              let sectionLevel = 0;
              let sectionEnd = lines.length;

              for (let i = 0; i < lines.length; i++) {
                const match = lines[i].match(sectionRegex);
                if (match) {
                  const headerText = match[2].toLowerCase();
                  const searchSection = args.section.toLowerCase();

                  if (
                    sectionStart === -1 &&
                    headerText.includes(searchSection)
                  ) {
                    sectionStart = i;
                    sectionLevel = match[1].length;
                  } else if (sectionStart !== -1 && i > sectionStart) {
                    // Found next section at same or higher level
                    if (match[1].length <= sectionLevel) {
                      sectionEnd = i;
                      break;
                    }
                  }
                }
              }

              if (sectionStart === -1) {
                // List available sections for error message
                const sections: string[] = [];
                for (const line of lines) {
                  const match = line.match(sectionRegex);
                  if (match) {
                    sections.push(match[2]);
                  }
                }
                return `Section "${args.section}" not found. Available sections: ${sections.join(", ")}`;
              }

              // Replace section content
              const before = lines.slice(0, sectionStart + 1);
              const after = lines.slice(sectionEnd);
              const newContent = [...before, args.content, ...after].join("\n");

              await Bun.write(planPath, newContent);

              return `Section "${args.section}" updated successfully.`;
            } catch (error) {
              return `Error updating plan: ${error instanceof Error ? error.message : String(error)}`;
            }
          },
        }),

        plan_delete: tool({
          description:
            "[custom-utils] Delete the current session's plan. Use this when you want to start over or clean up.",
          args: {},
          async execute(_args, context) {
            const planPath = getPlanPath(context);

            try {
              if (!existsSync(planPath)) {
                return "No plan found for this session.";
              }

              await unlink(planPath);

              return "Plan deleted successfully.";
            } catch (error) {
              return `Error deleting plan: ${error instanceof Error ? error.message : String(error)}`;
            }
          },
        }),
      },
    };
  },
};

export default CustomUtilsPlugin;
