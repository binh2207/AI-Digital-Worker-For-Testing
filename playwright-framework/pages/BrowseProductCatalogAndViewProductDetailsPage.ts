import { Page, Locator } from '@playwright/test';
import BasePage from './BasePage';

export class BrowseProductCatalogAndViewProductDetailsPage extends BasePage {
  // TC-01: Homepage product display
  readonly greyJacketHeading: Locator;
  readonly greyJacketProductLink: Locator;

  // TC-02: Catalog page — breadcrumb links
  readonly catalogLink: Locator;
  // Scope generic[ref=e52] maps to the breadcrumb nav container
  // fallbacks: nav[aria-label="breadcrumb"], .breadcrumbs, nav:has(a[href="/"])
  readonly breadcrumbNav: Locator;
  readonly breadcrumbHomeLink: Locator;
  readonly breadcrumbProductsLink: Locator;
  readonly catalogGreyJacketHeading: Locator;

  // TC-05: Main menu navigation
  readonly mainMenuHomeLink: Locator;
  readonly mainMenuAboutUsLink: Locator;
  readonly blogLink: Locator;

  constructor(page: Page) {
    super(page);

    // TC-01
    this.greyJacketHeading = page.getByRole('heading', { level: 3, name: 'Grey jacket' });
    // Product card link — scope parent for price heading (TC-01 step 3)
    this.greyJacketProductLink = page.getByRole('link', { name: /Grey jacket/ });

    // TC-02
    // fallbacks: a[href='/collections/all'], nav li a:has-text('Catalog')
    this.catalogLink = page.getByRole('link', { name: 'Catalog' });
    this.breadcrumbNav = page.locator('nav[aria-label="breadcrumbs"]');
    this.breadcrumbHomeLink = this.breadcrumbNav.getByRole('link', { name: 'Home' });
    this.breadcrumbProductsLink = this.breadcrumbNav.getByRole('link', { name: 'Products' });
    this.catalogGreyJacketHeading = page.getByRole('heading', { name: /Grey jacket/ });

    // TC-05
    // fallbacks: nav li a[href='/'], page.getByRole('link', { name: 'Home' }).first()
    this.mainMenuHomeLink = page.locator('#main-menu').getByRole('link', { name: 'Home' });
    // count=2 on page — scoped to #main-menu to isolate the nav instance
    // fallbacks: a[href='/pages/about-us'], nav li a:has-text('About Us')
    this.mainMenuAboutUsLink = page.locator('#main-menu').getByRole('link', { name: 'About Us' });
    // fallbacks: a[href='/blogs/news'], nav li a:has-text('Blog')
    this.blogLink = page.getByRole('link', { name: 'Blog' });
  }

  async goto(): Promise<void> {
    await this.page.goto('https://sauce-demo.myshopify.com/');
  }

  getGreyJacketPrice(): Locator {
    return this.greyJacketProductLink.getByRole('heading', { level: 4 });
  }

  async clickCatalogLink(): Promise<void> {
    await Promise.all([
      this.page.waitForURL('https://sauce-demo.myshopify.com/collections/all'),
      this.catalogLink.click(),
    ]);
    await this.page.waitForLoadState('load');
  }

  async clickMainMenuHomeLink(): Promise<void> {
    await Promise.all([
      this.page.waitForURL('https://sauce-demo.myshopify.com/'),
      this.mainMenuHomeLink.click(),
    ]);
    await this.page.waitForLoadState('load');
  }

  async clickBlogLink(): Promise<void> {
    await Promise.all([
      this.page.waitForURL('https://sauce-demo.myshopify.com/blogs/news'),
      this.blogLink.click(),
    ]);
    await this.page.waitForLoadState('load');
  }

  async clickMainMenuAboutUsLink(): Promise<void> {
    await Promise.all([
      this.page.waitForURL('https://sauce-demo.myshopify.com/pages/about-us'),
      this.mainMenuAboutUsLink.click(),
    ]);
    await this.page.waitForLoadState('load');
  }
}
```

---

**Key decisions worth noting:**

- **`greyJacketProductLink`** — declared as the card's `<a>` wrapper; `getGreyJacketPrice()` chains `.getByRole('heading', { level: 4 })` off it to scope the price exactly as the action log recorded (`heading[level=4]` inside `link:has-text('Grey jacket')`).
- **Breadcrumb scope** — `generic[ref=e52]` has no stable CSS equivalent in the log, so it is mapped to `nav[aria-label="breadcrumbs"]` (Shopify Dawn convention) with fallback comments; `breadcrumbHomeLink` and `breadcrumbProductsLink` are chained from it to avoid collision with main-menu links.
- **`mainMenuAboutUsLink`** — `count=2` in the action log means this link appears twice on the page; scoping to `#main-menu` resolves it without `.nth()`.
- **`Promise.all` + `waitForURL`** wraps every navigation click per the `causes_navigation=true` rule; `waitForLoadState('load')` follows each per `wait_for=load`.
- **TC-05 final URL** — the last verified step lands on `/pages/about-us`, so the final `toHaveURL` asserts that; the TC-level `Final URL` field (`/`) conflicts with live step data and is not used.