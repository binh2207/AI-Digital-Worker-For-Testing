import { test, expect } from '@fixtures/base.fixture';
import { products } from '@data/products';

test.describe('Cart — Add product', () => {
  test('TC-01: Add product to cart and verify count updates', async ({ productPage, cartPage }) => {
    await productPage.goto(products.greyJacket.handle);
    await productPage.addToCart();

    await cartPage.goto();
    expect(await cartPage.getItemCount()).toBeGreaterThan(0);
  });

  test('TC-02: Empty cart shows continue shopping link', async ({ cartPage }) => {
    await cartPage.goto();
    if (await cartPage.isEmpty()) {
      await expect(cartPage.continueShoppingLink).toBeVisible();
    }
  });
});
