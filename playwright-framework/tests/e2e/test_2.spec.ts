
```typescript
import { test, expect } from '@playwright/test';
import { SelectVariantsAndAddProductsToCartPage } from '../../pages/SelectVariantsAndAddProductsToCartPage';

const PRODUCT_HANDLE = 'grey-jacket';

test.describe('TEST-2 — Select variants and add products to cart', () => {
  // SKIP TC-01: Only one combobox exists with a single "Grey jacket" option — no Size (S/M/L) or Color dropdown present on the live product page
  // SKIP TC-02: Non-UI criterion — requires DOM/source inspection, excluded per test instructions

  test('TC-03: "Add to Cart" button is visible and submits the product form', async ({ page }) => {
    const cartPage = new SelectVariantsAndAddProductsToCartPage(page);
    await cartPage.gotoProduct(PRODUCT_HANDLE);
    await expect(cartPage.addToCartButton).toBeVisible();
    await cartPage.addToCart();
    expect(cartPage.getCurrentUrl()).toContain('/products/');
  });

  test('TC-04: Cart icon/count updates after a successful add', async ({ page }) => {
    const cartPage = new SelectVariantsAndAddProductsToCartPage(page);
    await cartPage.gotoProduct(PRODUCT_HANDLE);
    expect(await cartPage.getCartHeaderBadgeText()).toContain('My Cart (0)');
    await cartPage.addToCart();
    expect(await cartPage.getCartHeaderBadgeText()).toContain('My Cart (1)');
  });

  test('TC-05: Cart page lists items with price, or shows empty-state with "Continue Shopping"', async ({ page }) => {
    const cartPage = new SelectVariantsAndAddProductsToCartPage(page);

    // Empty-state branch
    await cartPage.gotoCart();
    await expect(cartPage.emptyCartMessage).toBeVisible();
    await expect(cartPage.continueShoppingLink).toBeVisible();
    await expect(cartPage.continueShoppingLink).toHaveAttribute('href', /\/collections\/all/);

    // Non-empty branch
    await cartPage.gotoProduct(PRODUCT_HANDLE);
    await cartPage.addToCart();
    await cartPage.gotoCart();
    await expect(cartPage.cartItemName).toBeVisible();
    await expect(cartPage.cartItemPrice).toBeVisible();
    await expect(cartPage.continueShoppingLink).toBeVisible();
  });
});