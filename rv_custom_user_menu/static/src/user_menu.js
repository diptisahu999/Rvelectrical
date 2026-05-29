/** @odoo-module **/

import { registry } from "@web/core/registry";

const userMenuRegistry = registry.category("user_menuitems");

// Remove the default static user menu items
userMenuRegistry.remove("documentation");
userMenuRegistry.remove("support");
userMenuRegistry.remove("odoo_account");
userMenuRegistry.remove("install_pwa");

// The "Onboarding" item is added dynamically when the tour_service starts.
// We must create a service that depends on tour_service so it runs after tour_service has started,
// and then we can safely remove the menu item.
export const customUserMenuService = {
    dependencies: ["tour_service"],
    start(env, { tour_service }) {
        registry.category("user_menuitems").remove("web_tour.tour_enabled");
    }
};

registry.category("services").add("custom_user_menu_service", customUserMenuService);

