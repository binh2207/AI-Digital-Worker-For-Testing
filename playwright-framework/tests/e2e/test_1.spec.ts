import { test, expect } from '@playwright/test';
import { BrowseProductCatalogAndViewProductDetailsPage } from '../../pages/BrowseProductCatalogAndViewProductDetailsPage';

test.describe('TEST-1 — Browse product catalog and view product details', () => {

  test('TC-01: Homepage displays featured products with name and price', async ({ page }) => {
    const catalogPage = new BrowseProductCatalogAndViewProductDetailsPage(page);

    await catalogPage.goto('/');

    await expect(catalogPage.greyJacketCardLink).toBeVisible();
    await expect(catalogPage.greyJacketNameHeading).toHaveText('Grey jacket');
    await expect(catalogPage.greyJacketPriceHeading).toHaveText('£55.00');
    await expect(page).toHaveURL('https://sauce-demo.myshopify.com/');
  });

  test('TC-02: Catalog page lists all products with breadcrumb navigation', async ({ page }) => {
    const catalogPage = new BrowseProductCatalogAndViewProductDetailsPage(page);

    await catalogPage.goto('/');
    await catalogPage.clickMainMenuCatalog();

    await expect(catalogPage.breadcrumbContainer).toContainText('Home — Products');
    await expect(catalogPage.greyJacketCardLink).toBeVisible();
    await expect(page).toHaveURL(/\/collections\/all/);
  });

  // SKIP TC-03: Grey jacket detail page has only one combobox variant (single 'Grey jacket' option) — no separate Size or Color selectors found

  test('TC-04: Sold-out products are clearly labeled', async ({ page }) => {
    const catalogPage = new BrowseProductCatalogAndViewProductDetailsPage(page);

    await catalogPage.goto('/collections/all');

    await expect(catalogPage.whiteSandalsSoldOutBadge).toBeVisible();
    await expect(catalogPage.whiteSandalsCardLink).toContainText('Sold Out');
    await expect(catalogPage.brownShadesSoldOutBadge).toBeVisible();
    await expect(catalogPage.brownShadesCardLink).toContainText('Sold Out');
    await expect(page).toHaveURL(/\/collections\/all/);
  });

  test('TC-05: User can navigate between Home, Catalog, Blog, and About Us from the main menu', async ({ page }) => {
    const catalogPage = new BrowseProductCatalogAndViewProductDetailsPage(page);

    await catalogPage.goto('/');
    await catalogPage.clickMainMenuHome();
    await expect(page).toHaveURL('https://sauce-demo.myshopify.com/');

    await catalogPage.clickMainMenuCatalog();
    await expect(page).toHaveURL(/\/collections\/all/);

    await catalogPage.clickMainMenuBlog();
    await expect(page).toHaveURL(/\/blogs\/news/);

    await catalogPage.clickMainMenuAboutUs();
    await expect(page).toHaveURL(/\/pages\/about-us/);
  });

});