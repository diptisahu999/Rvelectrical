/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { markup } from "@odoo/owl";
import { KanbanColumnQuickCreate } from "@web/views/kanban/kanban_column_quick_create";
import { KanbanColumnExamplesDialog } from "@web/views/kanban/kanban_column_examples_dialog";
import { patch } from "@web/core/utils/patch";

// Define bullets for visual consistency
const greenBullet = markup(`<span class="o_status d-inline-block o_status_green"></span>`);
const orangeBullet = markup(`<span class="o_status d-inline-block text-warning"></span>`);
const blueBullet = markup(`<span class="o_status d-inline-block text-info"></span>`);
const purpleBullet = markup(`<span class="o_status d-inline-block text-primary"></span>`);

// Enhanced project examples with stage templates
let enhancedProjectExamples = null;

async function loadStageTemplates() {
    try {
        const templates = await rpc("/web/dataset/call_kw/project.stage.template/search_read", {
            model: "project.stage.template",
            method: "search_read",
            args: [[]],
            kwargs: {
                fields: ["name", "description"],
            },
        });

        const templateExamples = [];

        for (const template of templates) {
            const stages = await rpc("/web/dataset/call_kw/project.stage.template.stage/search_read", {
                model: "project.stage.template.stage",
                method: "search_read",
                args: [[["template_id", "=", template.id]]],
                kwargs: {
                    fields: ["name", "sequence", "fold"],
                    order: "sequence asc",
                },
            });

            const columns = stages.filter(stage => !stage.fold).map(stage => stage.name);
            const foldedColumns = stages.filter(stage => stage.fold).map(stage => stage.name);

            templateExamples.push({
                name: `📋 ${template.name}`, // Add icon to distinguish from default examples
                columns: columns,
                foldedColumns: foldedColumns,
                isCustomTemplate: true,
                templateId: template.id,
                get description() {
                    return template.description || _t("Custom stage template for project management");
                },
                bullets: [greenBullet, orangeBullet, blueBullet, purpleBullet].slice(0, Math.min(4, columns.length)),
            });
        }

        return templateExamples;
    } catch (error) {
        console.error("Failed to load stage templates:", error);
        return [];
    }
}

async function getEnhancedProjectExamples() {
    if (enhancedProjectExamples) {
        return enhancedProjectExamples;
    }

    // Get original project examples
    const originalData = registry.category("kanban_examples").get('project', {});
    
    // Load custom stage templates
    const customTemplates = await loadStageTemplates();

    // Create enhanced examples data
    enhancedProjectExamples = {
        ...originalData,
        examples: [
            ...customTemplates, // Custom templates first
            ...(originalData.examples || [])
        ],
        applyExamplesText: _t("Use This For My Project"),
    };

    return enhancedProjectExamples;
}

// Patch KanbanColumnQuickCreate to handle custom template application
patch(KanbanColumnQuickCreate.prototype, {
    
    async showExamples() {
        // Get enhanced examples including our stage templates
        const enhancedData = await getEnhancedProjectExamples();
        
        this.dialog.add(KanbanColumnExamplesDialog, {
            examples: enhancedData.examples,
            applyExamplesText: enhancedData.applyExamplesText || _t("Use This For My Kanban"),
            applyExamples: async (index) => {
                const selectedExample = enhancedData.examples[index];
                
                // Check if this is a custom stage template
                if (selectedExample.isCustomTemplate) {
                    await this._applyStageTemplate(selectedExample);
                } else {
                    // Apply standard example logic
                    const { foldField } = enhancedData;
                    const { columns, foldedColumns = [] } = selectedExample;
                    
                    for (const groupName of columns) {
                        this.props.onValidate(groupName);
                    }
                    for (const groupName of foldedColumns) {
                        this.props.onValidate(groupName, foldField);
                    }
                }
            },
        });
    },

    async _applyStageTemplate(templateExample) {
        try {
            // Create stages using the stage template
            const result = await rpc("/web/dataset/call_kw/project.stage.template/apply_template_to_project", {
                model: "project.stage.template",
                method: "apply_template_to_project",
                args: [templateExample.templateId],
                kwargs: {
                    context: this.env.searchModel?.context || {},
                },
            });

            // If successful, create the column names in the kanban view
            const { columns, foldedColumns = [] } = templateExample;
            const foldField = "fold"; // Project stages use 'fold' field
            
            for (const groupName of columns) {
                this.props.onValidate(groupName);
            }
            for (const groupName of foldedColumns) {
                this.props.onValidate(groupName, foldField);
            }

        } catch (error) {
            console.error("Failed to apply stage template:", error);
            // Fallback to standard column creation
            const { columns, foldedColumns = [] } = templateExample;
            for (const groupName of columns) {
                this.props.onValidate(groupName);
            }
            for (const groupName of foldedColumns) {
                this.props.onValidate(groupName, "fold");
            }
        }
    }
});

// Initialize enhanced examples on module load
(async () => {
    const enhancedData = await getEnhancedProjectExamples();
    registry.category("kanban_examples").add('project', enhancedData, { force: true });
})();
