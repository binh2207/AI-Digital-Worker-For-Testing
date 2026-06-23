import { Page, Locator } from '@playwright/test';
import BasePage from './BasePage';

export class BrowseProductCatalogAndViewProductDetailsPage extends BasePage {
  // Grey jacket product card — appears on homepage featured section and catalog page
  readonly greyJacketCardLink: Locator;
  // Product name heading scoped inside the Grey jacket card link
  readonly greyJacketNameHeading: Locator;
  // Price heading scoped inside the Grey jacket card link
  // fallback: this.greyJacketCardLink.getByText('£55.00', { exact: true })
  readonly greyJacketPriceHeading: Locator;

  // Breadcrumb navigation rendered on collection/catalog pages
  // fallback: page.locator('[aria-label*="breadcrumb"]'), page.locator('nav.breadcrumb')
  readonly breadcrumbContainer: Locator;

  // White sandals — sold-out product card on catalog page
  readonly whiteSandalsCardLink: Locator;
  readonly whiteSandalsSoldOutBadge: Locator;

  // Brown Shades — sold-out product card on catalog page
  readonly brownShadesCardLink: Locator;
  readonly brownShadesSoldOutBadge: Locator;

  // Main menu navigation — all scoped to #main-menu as recorded
  // fallbacks: a[href='/'], a[href='/collections/all'], a[href='/blogs/news'], a[href='/pages/about-us']
  readonly mainMenuHomeLink: Locator;
  readonly mainMenuCatalogLink: Locator;
  readonly mainMenuBlogLink: Locator;
  readonly mainMenuAboutUsLink: Locator;

  constructor(page: Page) {
    super(page);

    this.greyJacketCardLink = page.getByRole('link', { name: /Grey jacket/ });
    this.greyJacketNameHeading = this.greyJacketCardLink.getByRole('heading', { name: 'Grey jacket' });
    this.greyJacketPriceHeading = this.greyJacketCardLink.getByRole('heading', { name: '£55.00' });

    this.breadcrumbContainer = page.locator('.breadcrumbs');

    this.whiteSandalsCardLink = page.getByRole('link', { name: /White sandals/ });
    this.whiteSandalsSoldOutBadge = this.whiteSandalsCardLink.getByText('Sold Out');

    this.brownShadesCardLink = page.getByRole('link', { name: /Brown Shades/ });
    this.brownShadesSoldOutBadge = this.brownShadesCardLink.getByText('Sold Out');

    this.mainMenuHomeLink = page.locator('#main-menu').getByRole('link', { name: 'Home' });
    this.mainMenuCatalogLink = page.locator('#main-menu').getByRole('link', { name: 'Catalog' });
    this.mainMenuBlogLink = page.locator('#main-menu').getByRole('link', { name: 'Blog' });
    this.mainMenuAboutUsLink = page.locator('#main-menu').getByRole('link', { name: 'About Us' });
  }

  async goto(path = '/'): Promise<void> {
    await this.page.goto(`https://sauce-demo.myshopify.com${path}`);
  }

  async clickMainMenuHome(): Promise<void> {
    await Promise.all([
      this.page.waitForURL('https://sauce-demo.myshopify.com/'),
      this.mainMenuHomeLink.click(),
    ]);
    await this.page.waitForLoadState('load');
  }

  async clickMainMenuCatalog(): Promise<void> {
    await Promise.all([
      this.page.waitForURL('https://sauce-demo.myshopify.com/collections/all'),
      this.mainMenuCatalogLink.click(),
    ]);
    await this.page.waitForLoadState('load');
  }

  async clickMainMenuBlog(): Promise<void> {
    await Promise.all([
      this.page.waitForURL('https://sauce-demo.myshopify.com/blogs/news'),
      this.mainMenuBlogLink.click(),
    ]);
    await this.page.waitForLoadState('load');
  }

  async clickMainMenuAboutUs(): Promise<void> {
    await Promise.all([
      this.page.waitForURL('https://sauce-demo.myshopify.com/pages/about-us'),
      this.mainMenuAboutUsLink.click(),
    ]);
    await this.page.waitForLoadState('load');
  }
}