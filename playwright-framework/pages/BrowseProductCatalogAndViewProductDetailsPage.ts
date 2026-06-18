import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

export class BrowseProductCatalogAndViewProductDetailsPage extends BasePage {
  // Homepage featured products
  readonly greyJacketLink: Locator;
  readonly noirJacketLink: Locator;
  readonly stripedTopLink: Locator;

  // Navigation links
  // fallbacks: ["a[href='/collections/all']", "page.locator('nav li').filter({ hasText: 'Catalog' }).getByRole('link')"]
  readonly catalogNavLink: Locator;
  // fallbacks: ["a[href='/']", "page.locator('nav[ref=e30]').getByRole('link', { name: 'Home' })"]
  readonly homeNavLink: Locator;
  // fallbacks: ["a[href='/blogs/news']"]
  readonly blogNavLink: Locator;
  // fallbacks: ["a[href='/pages/about-us']"]
  readonly aboutUsNavLink: Locator;

  // Breadcrumb (TC-02) — .first() used because 'Home' appears in both breadcrumb and main nav
  readonly breadcrumbHomeLink: Locator;
  readonly breadcrumbProductsLink: Locator;

  // Catalog page
  readonly productsHeading: Locator;

  // Product detail (TC-03)
  readonly noirJacketHeading: Locator;
  readonly noirJacketPrice: Locator;
  readonly sizeCombobox: Locator;
  readonly colorCombobox: Locator;
  // fallbacks: ['.product-description'] — .first() per action log; match=contains
  readonly productDescription: Locator;

  constructor(page: Page) {
    super(page);

    this.greyJacketLink = page.getByRole('link', { name: /Grey jacket/ });
    this.noirJacketLink = page.getByRole('link', { name: /Noir jacket/ });
    this.stripedTopLink = page.getByRole('link', { name: /Striped top/ });

    this.catalogNavLink = page.getByRole('link', { name: 'Catalog' });
    this.homeNavLink = page.locator('#main-menu').getByRole('link', { name: 'Home' });
    this.blogNavLink = page.getByRole('link', { name: 'Blog' });
    this.aboutUsNavLink = page.locator('#main-menu').getByRole('link', { name: 'About Us' });

    this.breadcrumbHomeLink = page.getByRole('link', { name: 'Home' }).first();
    this.breadcrumbProductsLink = page.getByRole('link', { name: 'Products' });

    this.productsHeading = page.getByRole('heading', { name: 'Products', level: 1 });

    this.noirJacketHeading = page.getByRole('heading', { name: 'Noir jacket', level: 1 });
    this.noirJacketPrice = page.getByRole('heading', { name: '£60.00', level: 2 });
    this.sizeCombobox = page.getByRole('combobox', { name: 'Size' });
    this.colorCombobox = page.getByRole('combobox', { name: 'Color' });
    this.productDescription = page.locator('.product__description, .product-description, .rte');
  }

  async gotoHomepage(): Promise<void> {
    await this.page.goto('https://sauce-demo.myshopify.com/');
  }

  async gotoCatalog(): Promise<void> {
    await this.page.goto('https://sauce-demo.myshopify.com/collections/all');
  }

  async clickCatalogLink(): Promise<void> {
    await Promise.all([
      this.page.waitForURL('https://sauce-demo.myshopify.com/collections/all'),
      this.catalogNavLink.click(),
    ]);
    await this.page.waitForLoadState('load');
  }

  async clickNoirJacketLink(): Promise<void> {
    await Promise.all([
      this.page.waitForURL('https://sauce-demo.myshopify.com/products/noir-jacket'),
      this.noirJacketLink.click(),
    ]);
    await this.page.waitForLoadState('load');
  }

  async clickHomeInMainMenu(): Promise<void> {
    await Promise.all([
      this.page.waitForURL('https://sauce-demo.myshopify.com/'),
      this.homeNavLink.click(),
    ]);
    await this.page.waitForLoadState('load');
  }

  async clickBlogLink(): Promise<void> {
    await Promise.all([
      this.page.waitForURL('https://sauce-demo.myshopify.com/blogs/news'),
      this.blogNavLink.click(),
    ]);
    await this.page.waitForLoadState('load');
  }

  async clickAboutUsLink(): Promise<void> {
    await Promise.all([
      this.page.waitForURL('https://sauce-demo.myshopify.com/pages/about-us'),
      this.aboutUsNavLink.click(),
    ]);
    await this.page.waitForLoadState('load');
  }
}