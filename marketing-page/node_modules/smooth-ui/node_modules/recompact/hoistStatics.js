'use strict';

exports.__esModule = true;

var _hoistNonReactStatics = require('hoist-non-react-statics');

var _hoistNonReactStatics2 = _interopRequireDefault(_hoistNonReactStatics);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/**
 * Augments a higher-order component so that when used, it copies non-react
 * static properties from the base component to the new component. This is
 * helpful when using Recompose with libraries like Relay.

 * Note that this only hoists non-react statics. The following static properties
 * will not be hoisted: childContextTypes, contextTypes, defaultProps, displayName,
 * getDefaultProps, mixins, propTypes, and type. The following native static methods
 * will also be ignored: name, length, prototype, caller, arguments, and arity
 *
 * @static
 * @category Utilities
 * @param {HigherOrderComponent} hoc
 * @returns {HigherOrderComponent} A function that takes a component and returns a new component.
 * @example
 *
 * hoistStatics(withProps({foo: 'bar'}));
 */
var hoistStatics = function hoistStatics(hoc) {
  return function (BaseComponent) {
    var NewComponent = hoc(BaseComponent);
    (0, _hoistNonReactStatics2.default)(NewComponent, BaseComponent);
    return NewComponent;
  };
};

exports.default = hoistStatics;