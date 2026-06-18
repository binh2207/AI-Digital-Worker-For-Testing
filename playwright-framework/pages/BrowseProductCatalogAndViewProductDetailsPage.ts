import { Page, Locator } from '@playwright/test';
import BasePage from './BasePage';

export class BrowseProductCatalogAndViewProductDetailsPage extends BasePage {
  // Homepage — Grey jacket product card (Shopify duplicate-variant naming: "Grey jacket Grey jacket £55.00")
  readonly greyJacketCard: Locator;
  readonly greyJacketTitle: Locator;
  readonly greyJacketPrice: Locator;

  // Catalog page — breadcrumb and product grid
  readonly catalogNavLink: Locator;
  readonly breadcrumbNav: Locator;
  readonly breadcrumbHomeLink: Locator;
  readonly breadcrumbProductsLink: Locator;
  readonly blackHeelsCard: Locator;

  // Product detail page
  readonly productTitle: Locator;
  readonly productPrice: Locator;
  readonly sizeCombobox: Locator;
  readonly colorCombobox: Locator;
  readonly productDescription: Locator;

  // Main menu navigation (scoped to #main-menu to avoid ambiguity with footer/repeated links)
  readonly blogNavLink: Locator;
  readonly aboutUsNavLink: Locator;
  readonly homeNavLink: Locator;

  constructor(page: Page) {
    super(page);

    // Homepage product card — regex guards against "Grey jacket - Grey jacket" Shopify duplicate rendering
    this.greyJacketCard = page.getByRole('link', { name: /Grey jacket/ });
    this.greyJacketTitle = this.greyJacketCard.getByRole('heading', { name: 'Grey jacket' });
    // fallback: this.greyJacketCard.locator('h3:has-text("Grey jacket")')
    this.greyJacketPrice = this.greyJacketCard.getByRole('heading', { name: '£55.00' });
    // fallback: this.greyJacketCard.locator('[class*="price"]:has-text("£55.00")')

    // Catalog nav link — unique in the main menu
    this.catalogNavLink = page.getByRole('link', { name: 'Catalog' });
    // fallback: page.locator("a[href='/collections/all']")

    // Breadcrumb nav — the em dash (—) uniquely distinguishes it from the main navigation
    this.breadcrumbNav = page.getByRole('navigation').filter({ hasText: '—' });
    this.breadcrumbHomeLink = this.breadcrumbNav.getByRole('link', { name: 'Home' });
    this.breadcrumbProductsLink = this.breadcrumbNav.getByRole('link', { name: 'Products' });

    // Black heels product card — regex handles any Shopify variant suffix appended to the title
    this.blackHeelsCard = page.getByRole('link', { name: /Black heels/ });
    // fallback: page.locator("a[href='/collections/all/products/flower-print-jeans']")

    // Product detail page — level constraints prevent matching secondary headings
    this.productTitle = page.getByRole('heading', { level: 1 });
    this.productPrice = page.getByRole('heading', { level: 2 });
    this.sizeCombobox = page.getByRole('combobox', { name: 'Size' });
    this.colorCombobox = page.getByRole('combobox', { name: 'Color' });
    // Description is a non-interactive generic block; exact match prevents substring collision
    this.productDescription = page.getByText(
      'This area is populated by the product description.',
      { exact: true },
    );

    // Main menu links — scoped to #main-menu because "About Us" and "Home" can appear in footer (count > 1)
    this.blogNavLink = page.getByRole('link', { name: 'Blog' });
    // fallback: page.locator("a[href='/blogs/news']")
    this.aboutUsNavLink = page.locator('#main-menu').getByRole('link', { name: 'About Us' });
    // fallback: page.locator("a[href='/pages/about-us']")
    this.homeNavLink = page.locator('#main-menu').getByRole('link', { name: 'Home' });
    // fallback: page.locator('#main-menu').locator("a[href='/']")
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

  async clickBlackHeels(): Promise<void> {
    await Promise.all([
      this.page.waitForURL('https://sauce-demo.myshopify.com/products/flower-print-jeans'),
      this.blackHeelsCard.click(),
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

  async clickHomeLink(): Promise<void> {
    await Promise.all([
      this.page.waitForURL('https://sauce-demo.myshopify.com/'),
      this.homeNavLink.click(),
    ]);
    await this.page.waitForLoadState('load');
  }
}