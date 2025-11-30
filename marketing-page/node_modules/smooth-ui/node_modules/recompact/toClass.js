'use strict';

exports.__esModule = true;

var _react = require('react');

var _react2 = _interopRequireDefault(_react);

var _getDisplayName = require('./getDisplayName');

var _getDisplayName2 = _interopRequireDefault(_getDisplayName);

var _isClassComponent = require('./isClassComponent');

var _isClassComponent2 = _interopRequireDefault(_isClassComponent);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _possibleConstructorReturn(self, call) { if (!self) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return call && (typeof call === "object" || typeof call === "function") ? call : self; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function, not " + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass; }

/**
 * Takes a function component and wraps it in a class. This can be used as a
 * fallback for libraries that need to add a ref to a component, like Relay.
 *
 * If the base component is already a class, it returns the given component.
 *
 * @static
 * @category Higher-order-components
 * @returns {HigherOrderComponent} A function that takes a component and returns a new component.
 * @example
 *
 * const Component = toClass(() => <div />);
 * <Component ref="foo" /> // A ref can be used because Component is a class
 */

var toClass = function toClass(BaseComponent) {
  if ((0, _isClassComponent2.default)(BaseComponent)) {
    return BaseComponent;
  }

  var ToClass = function (_Component) {
    _inherits(ToClass, _Component);

    function ToClass() {
      _classCallCheck(this, ToClass);

      return _possibleConstructorReturn(this, _Component.apply(this, arguments));
    }

    ToClass.prototype.render = function render() {
      if (typeof BaseComponent === 'string') {
        return _react2.default.createElement(BaseComponent, this.props);
      }

      return BaseComponent(this.props, this.context);
    };

    return ToClass;
  }(_react.Component);

  ToClass.displayName = (0, _getDisplayName2.default)(BaseComponent);
  ToClass.propTypes = BaseComponent.propTypes;
  ToClass.contextTypes = BaseComponent.contextTypes;
  ToClass.defaultProps = BaseComponent.defaultProps;

  return ToClass;
};

exports.default = toClass;