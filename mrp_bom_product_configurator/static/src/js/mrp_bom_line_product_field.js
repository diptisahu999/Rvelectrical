/** @odoo-module **/

import { registry } from "@web/core/registry";
import { MrpBomProductConfiguratorDialog } from "./mrp_bom_product_configurator_dialog";
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
 * A simple button component that triggers the configurator without requiring a server save.
 */
export class MrpBomConfigButton extends Component {
    static template = "mrp_bom_product_configurator.ConfigButton";

    setup() {
        this.dialog = this.env.services.dialog;
    }

    onClick() {
        const record = this.props.record;
        if (!record.data.configuration_template_id) {
            return;
        }

        this.dialog.add(MrpBomProductConfiguratorDialog, {
            productTemplateId: record.data.configuration_template_id[0],
            ptavIds: [],
            customAttributeValues: [],
            quantity: record.data.product_qty || 1.0,
            productUOMId: record.data.product_uom_id ? record.data.product_uom_id[0] : false,
            companyId: record.model.root.data.company_id ? record.model.root.data.company_id[0] : false,
            save: async (product) => {
                await applyProduct(record, product);
            },
            discard: () => {},
        });
    }
}

registry.category("view_widgets").add("mrp_bom_config_button", {
    component: MrpBomConfigButton,
});
