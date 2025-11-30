'use strict';

exports.__esModule = true;

var _identity = require('./identity');

var _identity2 = _interopRequireDefault(_identity);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/**
 * This method is similar to lodash `flowRight`. It permits to easily compose
 * several high order components.
 *
 * @static
 * @category Utilities
 * @param {...Function} [funcs] The functions to invoke.
 * @returns {Function} Returns the new composite function.
 * @see https://lodash.com/docs/master#flowRight
 * @example
 *
 * const enhance = compose(pure, withProps({foo: 'bar'}));
 * const Component = enhance(MyComponent);
 */
function compose() {
  for (var _len = arguments.length, funcs = Array(_len), _key = 0; _key < _len; _key++) {
    funcs[_key] = arguments[_key];
  }

  if (funcs.length === 0) {
    return _identity2.default;
  }

  if (funcs.length === 1) {
    return funcs[0];
  }

  return funcs.reduce(function (a, b) {
    return function () {
      return a(b.apply(undefined, arguments));
    };
  });
}

exports.default = compose;