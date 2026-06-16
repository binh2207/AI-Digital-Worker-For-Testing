import { type Locator, type Page } from '@playwright/test';
import { BasePage } from './BasePage';

export class SelectVariantsAndAddProductsToCartPage extends BasePage {
  readonly variantCombobox: Locator;
  readonly addToCartButton: Locator;
  readonly cartHeaderLink: Locator;
  readonly cartItemName: Locator;
  readonly cartItemPrice: Locator;
  readonly continueShoppingLink: Locator;
  readonly emptyCartMessage: Locator;

  constructor(page: Page) {
    super(page);
    this.variantCombobox     = page.getByRole('combobox');
    this.addToCartButton     = page.getByRole('button', { name: /add to cart/i });
    this.cartHeaderLink      = page.getByRole('link', { name: /my cart/i });
    this.cartItemName        = page.getByText('Grey jacket');
    this.cartItemPrice       = page.getByText('£55.00');
    this.continueShoppingLink = page.getByRole('link', { name: /continue shopping/i });
    this.emptyCartMessage    = page.getByText('It appears that your cart is currently empty!');
  }

  async gotoProduct(): Promise<void> {
    await this.page.goto('/product/grey-jacket');
  }

  async gotoCart(): Promise<void> {
    await this.page.goto('/cart');
  }

  async clickAddToCart(): Promise<void> {
    await this.addToCartButton.click();
  }

  async getCartHeaderText(): Promise<string> {
    return (await this.cartHeaderLink.textContent()) ?? '';
  }
}