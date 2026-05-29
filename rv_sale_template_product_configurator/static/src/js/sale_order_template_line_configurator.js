/** @odoo-module **/

import { registry } from "@web/core/registry";
import { MrpBomProductConfiguratorDialog } from "@mrp_bom_product_configurator/js/mrp_bom_product_configurator_dialog";
import { x2ManyCommands } from "@web/core/orm_service";
import { Component } from "@odoo/owl";

async function applyProduct(record, product) {
    const customAttributesCommands = [
        x2ManyCommands.set([]),
    ];

    if (product.attribute_lines) {
        for (const ptal of product.attribute_lines) {
            const selectedCustomPTAV = ptal.attribute_values.find(
                ptav => ptav.is_custom && ptal.selected_attribute_value_ids.includes(ptav.id)
            );
            if (selectedCustomPTAV) {
                customAttributesCommands.push(
                    x2ManyCommands.create(undefined, {
                        custom_product_template_attribute_value_id: [selectedCustomPTAV.id, ""],
                        custom_value: ptal.customValue || "",
                    })
                );
            };
        }
    }

    await record.update({
        configuration_template_id: [product.product_tmpl_id, product.display_name],
        product_id: [product.id, product.display_name],
        product_custom_attribute_value_ids: customAttributesCommands,
    });
}

/**
 * A simple button component that triggers the configurator for Sale Order Template lines.
 */
export class SaleOrderTemplateConfigButton extends Component {
    static template = "mrp_bom_product_configurator.ConfigButton"; // Reuse the same template

    setup() {
        this.dialog = this.env.services.dialog;
    }

    onClick() {
        const record = this.props.record;
        let productTemplateId = record.data.configuration_template_id ? record.data.configuration_template_id[0] : false;
        
        // If template not set, try to get it from product_id
        if (!productTemplateId && record.data.product_id) {
            // This might require a fetch if not in the view, but usually it's there
            // However, our onchange in Python handles it.
            // But let's check product_id.product_tmpl_id if available (custom JS models might not have it)
            // Just return if still no template
        }

        if (!productTemplateId) {
            return;
        }

        this.dialog.add(MrpBomProductConfiguratorDialog, {
            productTemplateId: productTemplateId,
            ptavIds: [],
            customAttributeValues: [],
            quantity: record.data.product_uom_qty || 1.0,
            productUOMId: record.data.product_uom_id ? record.data.product_uom_id[0] : false,
            // company_id might be different? Sale order templates are usually company-specific if selected
            companyId: record.model.root.data.company_id ? record.model.root.data.company_id[0] : false,
            save: async (product) => {
                await applyProduct(record, product);
            },
            discard: () => {},
        });
    }
}

registry.category("view_widgets").add("sale_order_template_config_button", {
    component: SaleOrderTemplateConfigButton,
});
