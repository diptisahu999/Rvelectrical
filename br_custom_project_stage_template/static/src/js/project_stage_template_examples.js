/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { markup } from "@odoo/owl";

// Define bullets for visual consistency with existing examples
const greenBullet = markup(`<span class="o_status d-inline-block o_status_green"></span>`);
const orangeBullet = markup(`<span class="o_status d-inline-block text-warning"></span>`);
const blueBullet = markup(`<span class="o_status d-inline-block text-info"></span>`);
const purpleBullet = markup(`<span class="o_status d-inline-block text-primary"></span>`);

class StageTemplateExampleService {
    constructor() {
        this.templateExamples = [];
        this.loaded = false;
    }

    async loadStageTemplates() {
        if (this.loaded) {
            return this.templateExamples;
        }

        try {
            const templates = await rpc("/web/dataset/call_kw/project.stage.template/search_read", {
                model: "project.stage.template",
                method: "search_read",
                args: [[]],
                kwargs: {
                    fields: ["name", "description"],
                },
            });

            // Load stages for each template
            for (const template of templates) {
                const stages = await rpc("/web/dataset/call_kw/project.stage.template.line/search_read", {
                    model: "project.stage.template.line",
                    method: "search_read",
                    args: [[["template_id", "=", template.id]]],
                    kwargs: {
                        fields: ["name", "sequence", "fold"],
                        order: "sequence asc",
                    },
                });

                // Separate folded and unfolded stages
                const columns = stages.filter(stage => !stage.fold).map(stage => stage.name);
                const foldedColumns = stages.filter(stage => stage.fold).map(stage => stage.name);

                // Create example object
                const example = {
                    name: template.name,
                    columns: columns,
                    foldedColumns: foldedColumns,
                    isCustomTemplate: true,
                    templateId: template.id,
                    get description() {
                        return template.description || _t("Custom stage template: %s", template.name);
                    },
                    bullets: [greenBullet, orangeBullet, blueBullet, purpleBullet].slice(0, Math.min(4, columns.length)),
                };

                this.templateExamples.push(example);
            }

            this.loaded = true;
        } catch (error) {
            console.error("Failed to load stage templates:", error);
        }

        return this.templateExamples;
    }

    async getEnhancedExampleData() {
        // Get original project examples
        const originalData = registry.category("kanban_examples").get('project', {});
        
        // Load our custom templates
        const customTemplates = await this.loadStageTemplates();

        // Combine original examples with custom templates
        const enhancedExamples = [
            ...customTemplates, // Put custom templates first
            ...(originalData.examples || [])
        ];

        return {
            ...originalData,
            examples: enhancedExamples,
            applyExamplesText: _t("Use This For My Project"),
        };
    }
}

// Create service instance
const stageTemplateService = new StageTemplateExampleService();

// Override the original project examples with enhanced version
async function enhanceProjectExamples() {
    const enhancedData = await stageTemplateService.getEnhancedExampleData();
    
    // Re-register with enhanced data
    registry.category("kanban_examples").add('project', enhancedData, { force: true });
}

// Initialize when the module loads
enhanceProjectExamples();

// Export for potential future use
export { stageTemplateService };
