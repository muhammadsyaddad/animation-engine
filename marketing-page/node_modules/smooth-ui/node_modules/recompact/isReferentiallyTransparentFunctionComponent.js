'use strict';

exports.__esModule = true;

var _isClassComponent = require('./isClassComponent');

var _isClassComponent2 = _interopRequireDefault(_isClassComponent);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/**
 * Returns true if the given value is a referentially transparent function component.
 * A referentially transparent function component is a component without any other
 * thing expect taking some props and returning a component.
 *
 * This method is useful to apply some optimization.
 *
 * @static
 * @category Utilities
 * @param {*} value Any value
 * @returns {Boolean} Returns true if the given value is a referentially
 * transparent function component.
 * @example
 *
 * const Button = () => <button />;
 * isReferentiallyTransparentFunctionComponent(Button); // true
 */
var isReferentiallyTransparentFunctionComponent = function isReferentiallyTransparentFunctionComponent(Component) {
  return Boolean(typeof Component === 'function' && !(0, _isClassComponent2.default)(Component) && !Component.defaultProps && !Component.contextTypes && (process.env.NODE_ENV === 'production' || !Component.propTypes));
};

exports.default = isReferentiallyTransparentFunctionComponent;