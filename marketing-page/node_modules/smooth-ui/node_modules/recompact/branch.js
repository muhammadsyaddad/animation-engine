'use strict';

exports.__esModule = true;

var _createEagerFactory = require('./createEagerFactory');

var _createEagerFactory2 = _interopRequireDefault(_createEagerFactory);

var _createHelper = require('./createHelper');

var _createHelper2 = _interopRequireDefault(_createHelper);

var _identity = require('./identity');

var _identity2 = _interopRequireDefault(_identity);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/**
 * Accepts a test function and two higher-order components. The test function
 * is passed the props from the owner. If it returns true, the left higher-order
 * component is applied to BaseComponent; otherwise, the right higher-order
 * component is applied (defaults to identity).
 *
 * @static
 * @category Higher-order-components
 * @param {Function} test The test to apply.
 * @param {HigherOrderComponent} left The higher-order component applied if the result
 *  of the test is true.
 * @param {HigherOrderComponent} [right=identity] The higher-order component applied if the result
 *  of the test is false.
 * @returns {HigherOrderComponent} A function that takes a component and returns a new component.
 * @example
 *
 * // Add the logic or rendering nothing if the prop `count` equals to `0`.
 * branch(({count}) => count === 0, renderNothing)(MyComponent);
 */
var branch = function branch(test, left) {
  var right = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : _identity2.default;
  return function (BaseComponent) {
    var leftFactory = void 0;
    var rightFactory = void 0;

    return function (props) {
      if (test(props)) {
        leftFactory = leftFactory || (0, _createEagerFactory2.default)(left(BaseComponent));
        return leftFactory(props);
      }

      rightFactory = rightFactory || (0, _createEagerFactory2.default)(right(BaseComponent));
      return rightFactory(props);
    };
  };
};

exports.default = (0, _createHelper2.default)(branch, 'branch');