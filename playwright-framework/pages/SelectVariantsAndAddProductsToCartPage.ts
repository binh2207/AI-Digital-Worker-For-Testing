import { type Locator, type Page } from '@playwright/test';
import { BasePage } from './BasePage';

export class SelectVariantsAndAddProductsToCartPage extends BasePage {

  readonly addToCartButton: Locator;
  readonly cartBadge: Locator;
  readonly cartItemName: Locator;
  readonly cartItemPrice: Locator;
  readonly continueShoppingLink: Locator;
  readonly emptyCartMessage: Locator;

  constructor(page: Page) {
    super(page);
    this.addToCartButton       = page.locator('input[value="Add to Cart"]');
    this.cartBadge             = page.getByText(/My Cart \(\d+\)/);
    this.cartItemName          = page.getByText('Grey jacket');
    this.cartItemPrice         = page.getByText('£55.00');
    this.continueShoppingLink  = page.getByRole('link', { name: '« Continue Shopping' });
    this.emptyCartMessage      = page.getByText('It appears that your cart is currently empty!');
  }

  async goto(): Promise<void> {
    await this.page.goto('/products/grey-jacket');
  }

  async gotoCart(): Promise<void> {
    await this.page.goto('/cart');
  }

  async clickAddToCart(): Promise<void> {
    await this.addToCartButton.click();
  }

  async getCartCount(): Promise<number> {
    const text = await this.cartBadge.textContent();
    const match = text?.match(/\((\d+)\)/);
    return match ? parseInt(match[1], 10) : 0;
  }

}
```

**Notes on skipped cases:**
- **TC-01** is commented out — the live execution found no Size/Color dropdowns, so there is nothing to automate without fabricating locators.
- **TC-02** is non-UI and would require `page.evaluate()` DOM inspection; it is not suitable for a standard Playwright action-based spec.
- **TC-05** is split into two tests (`TC-05a`/`TC-05b`) to honour the one-assertion-focus rule: the items-present branch requires a prior `clickAddToCart()`, while the empty-state branch navigates directly to `/cart`, avoiding a dependency on a remove-item flow for which no locators were recorded.