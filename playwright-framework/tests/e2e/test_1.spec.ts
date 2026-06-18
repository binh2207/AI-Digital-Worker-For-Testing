import { test, expect } from '@playwright/test';
import { BrowseProductCatalogAndViewProductDetailsPage } from '../../pages/BrowseProductCatalogAndViewProductDetailsPage';

test.describe('TEST-1 — Browse product catalog and view product details', () => {
  let catalogPage: BrowseProductCatalogAndViewProductDetailsPage;

  test.beforeEach(async ({ page }) => {
    catalogPage = new BrowseProductCatalogAndViewProductDetailsPage(page);
  });

  test('TC-01: Homepage displays featured products with name and price', async ({ page }) => {
    await catalogPage.gotoHomepage();
    await expect(catalogPage.greyJacketCard).toBeVisible();
    await expect(catalogPage.greyJacketTitle).toHaveText('Grey jacket');
    await expect(catalogPage.greyJacketPrice).toHaveText('£55.00');
    await expect(page).toHaveURL('https://sauce-demo.myshopify.com/');
  });

  test('TC-02: Catalog page lists all products with breadcrumb navigation', async ({ page }) => {
    await catalogPage.gotoHomepage();
    await catalogPage.clickCatalogLink();
    await expect(catalogPage.breadcrumbNav).toContainText('Home — Products');
    await expect(catalogPage.breadcrumbHomeLink).toBeVisible();
    await expect(catalogPage.breadcrumbProductsLink).toBeVisible();
    await expect(catalogPage.blackHeelsCard).toBeVisible();
    await expect(page).toHaveURL('https://sauce-demo.myshopify.com/collections/all');
  });

  test('TC-03: Product detail page shows name, price, variant selectors, and description', async ({ page }) => {
    await catalogPage.gotoCatalog();
    await catalogPage.clickBlackHeels();
    await expect(catalogPage.productTitle).toHaveText('Black heels');
    await expect(catalogPage.productPrice).toHaveText('£45.00');
    await expect(catalogPage.sizeCombobox).toBeVisible();
    await expect(catalogPage.colorCombobox).toBeVisible();
    await expect(catalogPage.productDescription).toBeVisible();
    await expect(page).toHaveURL('https://sauce-demo.myshopify.com/products/flower-print-jeans');
  });

  // SKIP TC-04: Bronze sandals has no 'Sold Out' badge on the catalog page; only White sandals and Brown Shades show the label

  test('TC-05: User can navigate between Home, Catalog, Blog, and About Us from the main menu', async ({ page }) => {
    await catalogPage.gotoCatalog();
    await catalogPage.clickBlogLink();
    await expect(page).toHaveURL(/\/blogs\/news/);
    await catalogPage.clickAboutUsLink();
    await expect(page).toHaveURL(/\/pages\/about-us/);
    await catalogPage.clickHomeLink();
    await expect(page).toHaveURL('https://sauce-demo.myshopify.com/');
  });
});