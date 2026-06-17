import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

const PRODUCT_URL = 'https://sauce-demo.myshopify.com/collections/frontpage/products/grey-jacket';
const CART_URL    = 'https://sauce-demo.myshopify.com/cart';

export class SelectVariantsAndAddProductsToCartPage extends BasePage {
  // fallbacks: ["button[type='submit']", 'button#add-to-cart']
  readonly addToCartButton:         Locator;
  readonly cartLink:                Locator;
  // fallback: "select[data-option='option1']"
  readonly productSelectOption:     Locator;
  readonly cartItemHeading:         Locator;
  readonly itemPrice:               Locator;
  readonly continueShoppingAltLink: Locator;
  // fallback: "a[href*='quantity=0']"
  readonly removeItemLink:          Locator;
  readonly emptyCartMessage:        Locator;
  readonly continueShoppingLink:    Locator;

  constructor(page: Page) {
    super(page);
    this.addToCartButton         = page.getByRole('button', { name: 'Add to Cart' });
    this.cartLink                = page.getByRole('link', { name: /My Cart/ });
    this.productSelectOption     = page.locator('select#product-select-option-0');
    this.cartItemHeading         = page.getByRole('heading', { name: 'Grey jacket' });
    this.itemPrice               = page.locator('form').getByText('£55.00').first();
    this.continueShoppingAltLink = page.getByRole('link', { name: '« Continue Shopping' });
    this.removeItemLink          = page.getByRole('link', { name: 'x' });
    this.emptyCartMessage        = page.locator('p').filter({ hasText: 'cart is currently empty' });
    this.continueShoppingLink    = page.getByRole('link', { name: 'Continue Shopping' });
  }

  async gotoProductPage(): Promise<void> {
    await this.navigate(PRODUCT_URL);
  }

  async gotoCartPage(): Promise<void> {
    await this.navigate(CART_URL);
  }

  async clickAddToCart(): Promise<void> {
    await this.addToCartButton.click();
    await this.page.waitForLoadState('networkidle');
  }

  async selectProductVariant(value: string): Promise<void> {
    await this.productSelectOption.selectOption(value);
  }

  async clickRemoveItem(): Promise<void> {
    await this.removeItemLink.click();
    await this.page.waitForLoadState('load');
  }

  async getCartLinkText(): Promise<string> {
    return (await this.cartLink.textContent()) ?? '';
  }
}