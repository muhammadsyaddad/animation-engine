'use strict';

exports.__esModule = true;

var _getDisplayName = require('./getDisplayName');

var _getDisplayName2 = _interopRequireDefault(_getDisplayName);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/**
 * Returns a wrapped version of a React component's display name. For instance,
 * if the display name of `component` is `'Post'`, and `wrapperName` is `'mapProps'`,
 * the return value is `'mapProps(Post)'`. Most Recompose higher-order components
 * use `wrapDisplayName()`.
 *
 * @static
 * @category Higher-order-components
 * @param {ReactClass|ReactFunctionalComponent} component Component
 * @param {String} wrapperName Wrapper name
 * @returns {String} Returns a wrapped displayName of the component.
 * @example
 *
 * // Create a hoc that will log when a component will mount
 * wrapDisplayName(Button, 'wrap'); // will return wrap(Button)
 */
var wrapDisplayName = function wrapDisplayName(BaseComponent, wrapperName) {
  return wrapperName + '(' + (0, _getDisplayName2.default)(BaseComponent) + ')';
};

exports.default = wrapDisplayName;