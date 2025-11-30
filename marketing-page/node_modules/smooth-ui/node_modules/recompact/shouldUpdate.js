'use strict';

exports.__esModule = true;

var _react = require('react');

var _createHelper = require('./createHelper');

var _createHelper2 = _interopRequireDefault(_createHelper);

var _createCompactableHOC = require('./utils/createCompactableHOC');

var _createCompactableHOC2 = _interopRequireDefault(_createCompactableHOC);

var _updateProps = require('./utils/updateProps');

var _updateProps2 = _interopRequireDefault(_updateProps);

var _createEagerFactory = require('./createEagerFactory');

var _createEagerFactory2 = _interopRequireDefault(_createEagerFactory);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _possibleConstructorReturn(self, call) { if (!self) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return call && (typeof call === "object" || typeof call === "function") ? call : self; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function, not " + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass; }

/**
 * Higher-order component version of
 * [`shouldComponentUpdate()`](https://facebook.github.io/react/docs/react-component.html#shouldcomponentupdate).
 * The test function accepts both the current props and the next props.
 *
 * @static
 * @category Higher-order-components
 * @param {Function} test Receive two arguments, props and nextProps
 * @returns {HigherOrderComponent} A function that takes a component and returns a new component.
 * @example
 *
 * // Pure
 * shouldUpdate((props, nextProps) => shallowEqual(props, nextProps))
 */
var shouldUpdate = function shouldUpdate(test) {
  return (0, _createCompactableHOC2.default)((0, _updateProps2.default)(function (next) {
    var props = void 0;

    return function (nextProps) {
      if (!props || test(props, nextProps)) {
        next(nextProps);
      }

      props = nextProps;
    };
  }), function (BaseComponent) {
    var factory = (0, _createEagerFactory2.default)(BaseComponent);
    return function (_Component) {
      _inherits(_class, _Component);

      function _class() {
        _classCallCheck(this, _class);

        return _possibleConstructorReturn(this, _Component.apply(this, arguments));
      }

      _class.prototype.shouldComponentUpdate = function shouldComponentUpdate(nextProps) {
        return test(this.props, nextProps);
      };

      _class.prototype.render = function render() {
        return factory(this.props);
      };

      return _class;
    }(_react.Component);
  });
};

exports.default = (0, _createHelper2.default)(shouldUpdate, 'shouldUpdate');