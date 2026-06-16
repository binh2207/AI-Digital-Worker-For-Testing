```typescript
import { test, expect } from '@playwright/test';
import { SelectVariantsAndAddProductsToCartPage } from '../../pages/SelectVariantsAndAddProductsToCartPage';

// SKIP TC-01: Only one combobox with a single "Grey jacket" option exists — no separate Size or Color dropdowns present
// SKIP TC-02: Non-UI test — requires DevTools/DOM inspection, not observable through UI actions

test.describe('TEST-2 — Select variants and add products to cart', () => {

  test('TC-03: Add to Cart button is visible and submits the product form', async ({ page }) => {
    const cartPage = new SelectVariantsAndAddProductsToCartPage(page);

    await cartPage.gotoProduct();

    await expect(cartPage.addToCartButton).toBeVisible();

    const countBefore = await cartPage.getCartCount();
    await cartPage.addToCart();
    const countAfter = await cartPage.getCartCount();

    expect(countAfter).toBe(countBefore + 1);
  });

  test('TC-04: Cart badge count updates from 0 to 1 after a successful add', async ({ page }) => {
    const cartPage = new SelectVariantsAndAddProductsToCartPage(page);

    await cartPage.gotoProduct();

    const countBefore = await cartPage.getCartCount();
    expect(countBefore).toBe(0);

    await cartPage.addToCart();

    await expect(cartPage.cartBadge).toContainText('1');
    const countAfter = await cartPage.getCartCount();
    expect(countAfter).toBe(1);
  });

  test('TC-05A: Cart page lists the added item with its price', async ({ page }) => {
    const cartPage = new SelectVariantsAndAddProductsToCartPage(page);

    await cartPage.gotoProduct();
    await cartPage.addToCart();
    await cartPage.gotoCart();

    await expect(cartPage.cartLineItem).toBeVisible();
    await expect(cartPage.cartLineItemPrice).toContainText('£55.00');
  });

  test('TC-05B: Empty cart displays empty-state message and Continue Shopping link', async ({ page }) => {
    const cartPage = new SelectVariantsAndAddProductsToCartPage(page);

    await cartPage.gotoCart();

    await expect(cartPage.emptyCartMessage).toBeVisible();
    await expect(cartPage.continueShoppingLink).toBeVisible();
  });

});
```

---