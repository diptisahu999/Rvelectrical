/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Component, onWillStart, useState, useSubEnv } from "@odoo/owl";
import { Dialog } from '@web/core/dialog/dialog';
import { rpc } from "@web/core/network/rpc";

export class MrpBomProductTemplateAttributeLine extends Component {
    static template = 'mrp_bom_product_configurator.MrpBomProductTemplateAttributeLine';
    static props = { ptal: Object, productTmplId: Number };

    onAttributeChange(ptavId) {
        this.env.updateProductTemplateSelectedPTAV(this.props.productTmplId, this.props.ptal.id, ptavId);
    }

    onCustomValueInput(ptavId, value) {
        this.env.updatePTAVCustomValue(this.props.productTmplId, ptavId, value);
    }
}

export class MrpBomProduct extends Component {
    static components = { MrpBomProductTemplateAttributeLine };
    static template = 'mrp_bom_product_configurator.MrpBomProduct';
    static props = { product: Object };
}

export class MrpBomProductList extends Component {
    static components = { MrpBomProduct };
    static template = "mrp_bom_product_configurator.MrpBomProductList";
    static props = { products: Array };
}

export class MrpBomProductConfiguratorDialog extends Component {
    static components = { Dialog, MrpBomProductList };
    static template = 'mrp_bom_product_configurator.dialog';
    static props = {
        productTemplateId: Number,
        ptavIds: { type: Array, element: Number },
        customAttributeValues: { type: Array, element: Object },
        quantity: Number,
        productUOMId: { type: Number, optional: true },
        companyId: { type: Number, optional: true },
        save: Function,
        discard: Function,
        close: Function,
    };

    setup() {
        this.title = _t("Configure your product");
        this.rpc = rpc;
        this.state = useState({
            products: [],
        });

        useSubEnv({
            updateProductTemplateSelectedPTAV: this._updateProductTemplateSelectedPTAV.bind(this),
            updatePTAVCustomValue: this._updatePTAVCustomValue.bind(this),
        });

        onWillStart(async () => {
            const { products } = await this._loadData();
            this.state.products = products;
            for (const customValue of this.props.customAttributeValues) {
                this._updatePTAVCustomValue(
                    this.props.productTemplateId,
                    customValue.ptavId,
                    customValue.value
                );
            }
        });
    }

    async _loadData() {
        return this.rpc('/mrp_bom_product_configurator/get_values', {
            product_template_id: this.props.productTemplateId,
            quantity: this.props.quantity,
            product_uom_id: this.props.productUOMId,
            company_id: this.props.companyId,
            ptav_ids: this.props.ptavIds,
        });
    }

    async _createProduct(product) {
        const combination = product.attribute_lines.flatMap(ptal => ptal.selected_attribute_value_ids);
        return this.rpc('/mrp_bom_product_configurator/create_product', {
            product_template_id: product.product_tmpl_id,
            combination: combination,
        });
    }

    async _updateProductTemplateSelectedPTAV(productTmplId, ptalId, ptavId) {
        const product = this.state.products.find(p => p.product_tmpl_id === productTmplId);
        const ptal = product.attribute_lines.find(l => l.id === ptalId);
        ptal.selected_attribute_value_ids = [parseInt(ptavId)];
        
        const combination = product.attribute_lines.flatMap(l => l.selected_attribute_value_ids);
        const updatedValues = await this.rpc('/mrp_bom_product_configurator/update_combination', {
            product_template_id: product.product_tmpl_id,
            combination: combination,
            quantity: product.quantity,
            product_uom_id: this.props.productUOMId,
            company_id: this.props.companyId,
        });
        Object.assign(product, updatedValues);
    }

    _updatePTAVCustomValue(productTmplId, ptavId, customValue) {
        const product = this.state.products.find(p => p.product_tmpl_id === productTmplId);
        const ptal = product.attribute_lines.find(ptal => ptal.selected_attribute_value_ids.includes(ptavId));
        if (ptal) {
            ptal.customValue = customValue;
        }
    }

    isPossibleConfiguration() {
        return this.state.products.every(p => 
            p.attribute_lines.every(l => l.selected_attribute_value_ids.length > 0)
        );
    }

    async onConfirm() {
        const product = this.state.products[0];
        if (!product.id) {
            const productId = await this._createProduct(product);
            product.id = parseInt(productId);
        }
        await this.props.save(product);
        this.props.close();
    }

    onDiscard() {
        this.props.discard();
        this.props.close();
    }
}
