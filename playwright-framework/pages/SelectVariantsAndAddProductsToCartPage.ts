import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

const PRODUCT_URL = 'https://sauce-demo.myshopify.com/collections/frontpage/products/grey-jacket';
const CART_URL    = 'https://sauce-demo.myshopify.com/cart';

export class SelectVariantsAndAddProductsToCartPage extends BasePage {
  readonly addToCartButton:    Locator;
  readonly cartLink:           Locator;
  readonly cartItemHeading:    Locator;
  readonly itemPrice:          Locator;
  readonly removeItemLink:     Locator;
  readonly emptyCartParagraph: Locator;
  readonly continueShoppingLink: Locator;

  constructor(page: Page) {
    super(page);
    this.addToCartButton     = page.getByRole('button', { name: 'Add to Cart' });
    this.cartLink            = page.getByRole('link', { name: /My Cart/ });
    this.cartItemHeading     = page.getByRole('heading', { name: 'Grey jacket - Grey jacket' });
    this.itemPrice           = page.getByText('£55.00');
    this.removeItemLink      = page.getByRole('link', { name: 'x' });
    this.emptyCartParagraph  = page.getByRole('paragraph');
    this.continueShoppingLink = page.getByRole('link', { name: 'Continue Shopping' });
  }

  async gotoProductPage(): Promise<void> {
    await this.navigate(PRODUCT_URL);
  }

  async gotoCartPage(): Promise<void> {
    await this.navigate(CART_URL);
  }

  async clickAddToCart(): Promise<void> {
    await this.addToCartButton.click();
  }

  async clickRemoveItem(): Promise<void> {
    await this.removeItemLink.click();
  }
}