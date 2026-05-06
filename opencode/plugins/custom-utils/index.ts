import { tool } from "@opencode-ai/plugin/tool";
import type { PluginModule } from "@opencode-ai/plugin";
import { mkdir, unlink, readdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import { homedir } from "node:os";
import { createHash } from "node:crypto";
import { basename } from "node:path";

function getOldPlanPath(context: { worktree: string; sessionID: string }): string {
  const worktreeHash = createHash("sha256")
    .update(context.worktree)
    .digest("hex")
    .slice(0, 8);
  const planDir = `${homedir()}/.config/opencode/plans`;
  return `${planDir}/${worktreeHash}-${context.sessionID}`;
}

// Alias for backward compatibility until tools are updated
function getPlanPath(context: { worktree: string; sessionID: string }): string {
  return getOldPlanPath(context);
}

function getDirectoryFromWorktree(worktree: string | undefined | null): string {
  if (!worktree || worktree.trim() === "") {
    return "unknown";
  }
  // Normalize path - remove trailing slashes
  const normalized = worktree.replace(/\/+$/, "");
  if (normalized === "/") {
    return "root";
  }
  return basename(normalized);
}

function generateTimestamp(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  const hours = String(now.getHours()).padStart(2, "0");
  const minutes = String(now.getMinutes()).padStart(2, "0");
  const seconds = String(now.getSeconds()).padStart(2, "0");
  return `${year}-${month}-${day}T${hours}-${minutes}-${seconds}`;
}

function getNewPlanPath(context: { worktree: string; sessionID: string }): string {
  const worktreeHash = createHash("sha256")
    .update(context.worktree)
    .digest("hex")
    .slice(0, 8);
  const directory = getDirectoryFromWorktree(context.worktree);
  const timestamp = generateTimestamp();
  const planDir = `${homedir()}/.config/opencode/plans/${worktreeHash}-${directory}`;
  return `${planDir}/${timestamp}-${context.sessionID}.md`;
}

function getNewPlanDir(context: { worktree: string }): string {
  const worktreeHash = createHash("sha256")
    .update(context.worktree)
    .digest("hex")
    .slice(0, 8);
  const directory = getDirectoryFromWorktree(context.worktree);
  return `${homedir()}/.config/opencode/plans/${worktreeHash}-${directory}`;
}

async function findPlanBySessionID(context: { worktree: string; sessionID: string }): Promise<string | null> {
  const planDir = getNewPlanDir(context);
  
  try {
    if (!existsSync(planDir)) {
      return null;
    }
    
    const files = await readdir(planDir);
    const matchingFile = files.find((file: string) => file.endsWith(`-${context.sessionID}.md`));
    
    if (matchingFile) {
      return `${planDir}/${matchingFile}`;
    }
    return null;
  } catch {
    return null;
  }
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
            const planPath = getNewPlanPath(context);
            const planDir = getNewPlanDir(context);

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
            try {
              // Check old location first (backward compatibility)
              const oldPlanPath = getOldPlanPath(context);
              if (existsSync(oldPlanPath)) {
                const content = await Bun.file(oldPlanPath).text();
                return content;
              }

              // Check new location (search by sessionID)
              const newPlanPath = await findPlanBySessionID(context);
              if (newPlanPath) {
                const content = await Bun.file(newPlanPath).text();
                return content;
              }

              return "No plan found for this session. Use plan_create to create one.";
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
            try {
              // Find plan using fallback logic (old location first, then new)
              let planPath: string | null = null;
              let isOldFormat = false;

              // Check old location first
              const oldPlanPath = getOldPlanPath(context);
              if (existsSync(oldPlanPath)) {
                planPath = oldPlanPath;
                isOldFormat = true;
              } else {
                // Check new location
                planPath = await findPlanBySessionID(context);
                isOldFormat = false;
              }

              if (!planPath) {
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

              // If old format, migrate to new location
              if (isOldFormat) {
                const newPlanPath = getNewPlanPath(context);
                const newPlanDir = getNewPlanDir(context);
                
                // Create directory if needed
                await mkdir(newPlanDir, { recursive: true });
                
                // Write to new location
                await Bun.write(newPlanPath, newContent);
                
                // Delete old file
                await unlink(planPath);
                
                return `Section "${args.section}" updated successfully. Plan migrated to new format.`;
              }

              // Write to existing location
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
            try {
              // Find plan using fallback logic (old location first, then new)
              let planPath: string | null = null;

              // Check old location first
              const oldPlanPath = getOldPlanPath(context);
              if (existsSync(oldPlanPath)) {
                planPath = oldPlanPath;
              } else {
                // Check new location
                planPath = await findPlanBySessionID(context);
              }

              if (!planPath) {
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
