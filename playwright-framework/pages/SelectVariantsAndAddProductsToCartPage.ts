
```typescript
import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

export class SelectVariantsAndAddProductsToCartPage extends BasePage {
  readonly addToCartButton: Locator;
  readonly cartHeaderBadge: Locator;
  readonly cartItemName: Locator;
  readonly cartItemPrice: Locator;
  readonly continueShoppingLink: Locator;
  readonly emptyCartMessage: Locator;

  constructor(page: Page) {
    super(page);
    this.addToCartButton = page.getByRole('button', { name: /add to cart/i });
    this.cartHeaderBadge = page.getByRole('link', { name: /My Cart/ });
    this.cartItemName = page.getByText('Grey jacket');
    this.cartItemPrice = page.getByText('£55.00');
    this.continueShoppingLink = page.getByRole('link', { name: 'Continue Shopping' });
    this.emptyCartMessage = page.getByText('It appears that your cart is currently empty!');
  }

  async gotoProduct(handle: string): Promise<void> {
    await this.navigate(`/products/${handle}`);
    await this.waitForPageLoad();
  }

  async gotoCart(): Promise<void> {
    await this.navigate('/cart');
    await this.waitForPageLoad();
  }

  async addToCart(): Promise<void> {
    await this.addToCartButton.click();
    await this.waitForPageLoad();
  }

  async getCartHeaderBadgeText(): Promise<string> {
    return this.cartHeaderBadge.innerText();
  }

  getCurrentUrl(): string {
    return this.page.url();
  }
}
```

---

**Key decisions explained:**

- **Existing PO replaced:** The file at `pages/SelectVariantsAndAddProductsToCartPage.ts` had the wrong class name (`SelectVariantsAndAddToCartPage`), a hardcoded `BASE_URL` constant (Playwright config owns that via `baseURL`), and full `page.goto(BASE_URL + path)` calls instead of `this.navigate(path)`. All fixed.
- **TC-05 tests both states in one test** — each `test()` gets a fresh browser context so the cart starts empty, allowing the empty-state assertion before the add-then-navigate flow for the non-empty state.
- **`cartHeaderBadge`** uses `/My Cart/` (no `i` flag) to match the exact casing `"My Cart (0)"` / `"My Cart (1)"` observed live; the regex anchors on text content so either count works with a single locator.
- **`continueShoppingLink` href assertion** is applied only in the empty-state branch where the live execution confirmed the target is `/collections/all`.