import { test as base, Page } from '@playwright/test';
import { ProductPage } from '@pages/ProductPage';
import { CartPage } from '@pages/CartPage';

type Fixtures = {
  productPage: ProductPage;
  cartPage: CartPage;
};

export const test = base.extend<Fixtures>({
  productPage: async ({ page }, use) => {
    await use(new ProductPage(page));
  },
  cartPage: async ({ page }, use) => {
    await use(new CartPage(page));
  },
});

export { expect } from '@playwright/test';
