```typescript
import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

export class SelectVariantsAndAddProductsToCartPage extends BasePage {
  readonly productPath = '/shop/grey-jacket';
  readonly cartPath = '/cart';

  readonly addToCartButton: Locator;
  readonly cartBadge: Locator;
  readonly cartItemName: Locator;
  readonly cartItemPrice: Locator;
  readonly emptyCartMessage: Locator;
  readonly continueShoppingLink: Locator;
  readonly removeItemButton: Locator;

  constructor(page: Page) {
    super(page);
    this.addToCartButton    = page.getByRole('button', { name: 'Add to Cart' });
    this.cartBadge          = page.getByRole('link', { name: /My Cart/ });
    this.cartItemName       = page.getByText('Grey jacket');
    this.cartItemPrice      = page.getByText('£55.00');
    this.emptyCartMessage   = page.getByText('It appears that your cart is currently empty!');
    this.continueShoppingLink = page.getByRole('link', { name: 'Continue Shopping' });
    this.removeItemButton   = page.getByRole('link', { name: /remove/i });
  }

  async gotoProduct(): Promise<void> {
    await this.page.goto(this.productPath);
  }

  async gotoCart(): Promise<void> {
    await this.page.goto(this.cartPath);
  }

  async clickAddToCart(): Promise<void> {
    await this.addToCartButton.click();
  }

  async removeFirstCartItem(): Promise<void> {
    await this.removeItemButton.first().click();
  }
}
```

---

**Key decisions:**

- **TC-03** asserts the button is visible before clicking, then uses `toHaveURL(new RegExp(productPath))` to confirm the page reloaded on the product URL (no redirect to an error page). The URL pattern is kept in the Page Object, not the spec.
- **TC-04** reads the badge text before and after `clickAddToCart()` using `toContainText` — tolerant of surrounding whitespace the site may inject.
- **TC-05** runs two phases in sequence: non-empty verification (item name + `£55.00`), then `removeFirstCartItem()` followed by empty-state assertions. `removeItemButton.first()` guards against multiple items accumulating from prior runs.
- `removeItemButton` uses `getByRole('link', { name: /remove/i })` — adjust the name pattern if the site's remove control uses a different label (e.g. `"Remove this item"` or an aria-label).