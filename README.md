International Specification for Control Descriptions in svg format.

## Use
Include an icon sprite set on your project with the following markup:

```html
<svg
  width="24"
  height="24"
  fill="none"
  stroke="currentColor"
  stroke-width="2"
  stroke-linecap="round"
  stroke-linejoin="round"
>
  <use xlink:href="path/to/icons/ioficons-sprite.svg#spur"/>
</svg>
```

**Note:** the `#spur` in example above you may change to current icon name. Please be patient to fill existing real icon name. Complete list check on [ioficon.osportup.com](https://osportup.com/ioficon).

Example above can simplyfied by single css class for all icons from the set and super simple svg link like this:

```css
.ioficons {
  width: 24px;
  height: 24px;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
  fill: none;
}
```
```html
<svg class="ioficons">
  <use xlink:href="path/to/icons/ioficon-sprite.svg#spur"/>
</svg>
```
