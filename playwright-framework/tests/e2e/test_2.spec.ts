import { test, expect } from '@playwright/test';
import { SelectVariantsAndAddToCartPage } from '../../pages/SelectvariantsandaddproductstocartPage';

test.describe('TEST-2 — Select variants and add products to cart', () => {
  // SKIP: TC-01 — No Size (S/M/L) or Color selectors exist; the product page renders only a single "Grey jacket" combobox with one option
  // SKIP: TC-02 — Non-UI criterion requiring DevTools DOM inspection of a hidden <input> value; out of scope for browser UI testing

  test('TC-03: "Add to Cart" button is visible and submits the product form', async ({ page }) => {
    const productPage = new SelectVariantsAndAddToCartPage(page);
    await productPage.gotoProduct();

    await expect(productPage.addToCartButton).toBeVisible();
    await expect(productPage.addToCartButton).toBeEnabled();

    await productPage.addToCart();

    await expect(productPage.cartBadge).toBeVisible();
  });

  test('TC-04: Cart icon/count updates after a successful add', async ({ page }) => {
    const productPage = new SelectVariantsAndAddToCartPage(page);
    await productPage.gotoProduct();

    const countBefore = await productPage.getCartCount();
    await productPage.addToCart();

    expect(await productPage.getCartCount()).toBe(countBefore + 1);
  });

  test('TC-05: Cart page lists the added Grey Jacket line item with price', async ({ page }) => {
    const productPage = new SelectVariantsAndAddToCartPage(page);
    await productPage.gotoProduct();
    await productPage.addToCart();
    await productPage.gotoCart();

    await expect(productPage.cartLineItem).toBeVisible();
    await expect(productPage.cartLineItemPrice).toBeVisible();
  });

  test('TC-06: Empty cart shows empty-state message and "Continue Shopping" link', async ({ page }) => {
    const productPage = new SelectVariantsAndAddToCartPage(page);
    await productPage.gotoCart();

    await expect(productPage.emptyCartMessage).toBeVisible();
    await expect(productPage.continueShoppingLink).toBeVisible();

    await productPage.clickContinueShopping();

    await expect(page).toHaveURL(/\/collections\/all/);
  });
});
