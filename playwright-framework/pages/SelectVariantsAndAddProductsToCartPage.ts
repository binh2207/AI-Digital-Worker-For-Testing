```typescript
import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

const BASE_URL = 'https://sauce-demo.myshopify.com';

export class SelectVariantsAndAddProductsToCartPage extends BasePage {
  readonly variantCombobox: Locator;
  readonly addToCartButton: Locator;
  readonly cartBadge: Locator;
  readonly cartLineItem: Locator;
  readonly cartLineItemPrice: Locator;
  readonly emptyCartMessage: Locator;
  readonly continueShoppingLink: Locator;

  constructor(page: Page) {
    super(page);
    this.variantCombobox = page.getByRole('combobox');
    this.addToCartButton = page.getByRole('button', { name: /add to cart/i });
    this.cartBadge = page.getByRole('link', { name: /my cart/i });
    this.cartLineItem = page.getByText(/grey jacket/i).first();
    this.cartLineItemPrice = page.getByText(/£\d+\.\d{2}/);
    this.emptyCartMessage = page.getByText('It appears that your cart is currently empty!');
    this.continueShoppingLink = page.getByRole('link', { name: 'Continue Shopping' });
  }

  async gotoProduct(): Promise<void> {
    await this.page.goto(`${BASE_URL}/products/grey-jacket`);
    await this.waitForPageLoad();
  }

  async gotoCart(): Promise<void> {
    await this.page.goto(`${BASE_URL}/cart`);
    await this.waitForPageLoad();
  }

  async addToCart(): Promise<void> {
    await this.addToCartButton.click();
  }

  async getCartCount(): Promise<number> {
    const text = await this.cartBadge.textContent();
    const match = text?.match(/\d+/);
    return match ? parseInt(match[0], 10) : 0;
  }

  async clickContinueShopping(): Promise<void> {
    await this.continueShoppingLink.click();
  }
}
```

---

**Key decisions:**

| | Rationale |
|---|---|
| TC-05 split into TC-05A / TC-05B | Two distinct scenarios (populated cart vs. empty cart) — each deserves an independent assertion focus |
| TC-03 assertion | Checks `countAfter === countBefore + 1` rather than hardcoding `1`, so it survives non-isolated runs |
| TC-04 assertion | Explicitly checks `countBefore === 0` first, then `countAfter === 1`, matching the exact badge transition observed live |
| `cartLineItemPrice` uses `toContainText('£55.00')` | Matches the regex locator (`/£\d+\.\d{2}/`) while asserting the exact observed value |
| `waitForPageLoad()` added to `gotoProduct()` / `gotoCart()` | Missing from the old page object — prevents race conditions on navigation |
| `variantCombobox` declared but not used in tests | Kept in Page Object for completeness; TC-01/TC-02 are skipped per rules |

The sandbox blocked direct file writes to `playwright-framework/`. If you grant write permission or approve the tool calls, I can write them immediately.