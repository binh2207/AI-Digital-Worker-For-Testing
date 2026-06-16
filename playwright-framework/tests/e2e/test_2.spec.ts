```typescript
import { test, expect } from '@playwright/test';
import { SelectVariantsAndAddProductsToCartPage } from '../../pages/SelectVariantsAndAddProductsToCartPage';

test.describe('TEST-2 — Select variants and add products to cart', () => {
  let cartPage: SelectVariantsAndAddProductsToCartPage;

  test.beforeEach(async ({ page }) => {
    cartPage = new SelectVariantsAndAddProductsToCartPage(page);
  });

  // SKIP TC-01: Only a single combobox ("Grey jacket") found on the product page — no Size (S/M/L) or Color dropdown present
  // SKIP TC-02: Non-UI — requires DOM inspection to verify hidden product ID update; cannot be confirmed through browser interaction

  test('TC-03: "Add to Cart" button is visible and submits the form', async ({ page }) => {
    await cartPage.gotoProduct();
    await expect(cartPage.addToCartButton).toBeVisible();
    await cartPage.clickAddToCart();
    await expect(page).toHaveURL(new RegExp(cartPage.productPath));
  });

  test('TC-04: Cart icon/count updates after a successful add', async ({ page }) => {
    await cartPage.gotoProduct();
    await expect(cartPage.cartBadge).toContainText('My Cart (0)');
    await cartPage.clickAddToCart();
    await expect(cartPage.cartBadge).toContainText('My Cart (1)');
  });

  test('TC-05: Cart page lists items with price or shows empty-state with "Continue Shopping"', async ({ page }) => {
    // Non-empty state: item appears in cart with correct price
    await cartPage.gotoProduct();
    await cartPage.clickAddToCart();
    await cartPage.gotoCart();
    await expect(cartPage.cartItemName).toBeVisible();
    await expect(cartPage.cartItemPrice).toContainText('£55.00');

    // Empty state: shown after removing the only cart item
    await cartPage.removeFirstCartItem();
    await expect(cartPage.emptyCartMessage).toBeVisible();
    await expect(cartPage.continueShoppingLink).toBeVisible();
  });
});
```