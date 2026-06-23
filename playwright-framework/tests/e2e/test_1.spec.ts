import { test, expect } from '@playwright/test';
import { BrowseProductCatalogAndViewProductDetailsPage } from '../../pages/BrowseProductCatalogAndViewProductDetailsPage';

test.describe('TEST-1 — Browse product catalog and view product details', () => {
  // SKIP TC-03: Only one unlabeled variant combobox (option 'Grey jacket') present; no separate Size or Color selectors found
  // SKIP TC-04: Bronze sandals shows 'Add to Cart' with no Sold Out label on catalog or detail page; White sandals correctly labeled

  test('TC-01: Homepage displays featured products with name and price', async ({ page }) => {
    const catalogPage = new BrowseProductCatalogAndViewProductDetailsPage(page);

    await catalogPage.goto();

    await expect(catalogPage.greyJacketHeading).toBeVisible();
    await expect(catalogPage.getGreyJacketPrice()).toContainText('£55.00');
  });

  test('TC-02: Catalog page lists all products with breadcrumb navigation', async ({ page }) => {
    const catalogPage = new BrowseProductCatalogAndViewProductDetailsPage(page);

    await catalogPage.goto();
    await catalogPage.clickCatalogLink();

    await expect(catalogPage.breadcrumbHomeLink).toBeVisible();
    await expect(catalogPage.breadcrumbProductsLink).toHaveText('Products');
    await expect(catalogPage.catalogGreyJacketHeading).toBeVisible();
    await expect(page).toHaveURL(/\/collections\/all/);
  });

  test('TC-05: User can navigate between Home, Catalog, Blog, and About Us from the main menu', async ({ page }) => {
    const catalogPage = new BrowseProductCatalogAndViewProductDetailsPage(page);

    await catalogPage.goto();

    await catalogPage.clickMainMenuHomeLink();
    await expect(page).toHaveURL('https://sauce-demo.myshopify.com/');

    await catalogPage.clickCatalogLink();
    await expect(page).toHaveURL(/\/collections\/all/);

    await catalogPage.clickBlogLink();
    await expect(page).toHaveURL(/\/blogs\/news/);

    await catalogPage.clickMainMenuAboutUsLink();
    await expect(page).toHaveURL(/\/pages\/about-us/);
  });
});