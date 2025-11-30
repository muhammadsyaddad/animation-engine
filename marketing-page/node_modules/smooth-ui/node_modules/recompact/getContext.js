'use strict';

exports.__esModule = true;

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

var _createHelper = require('./createHelper');

var _createHelper2 = _interopRequireDefault(_createHelper);

var _createEagerFactory = require('./createEagerFactory');

var _createEagerFactory2 = _interopRequireDefault(_createEagerFactory);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/**
 * Gets values from context and passes them along as props.
 *
 * @static
 * @category Higher-order-components
 * @param {Object} contextTypes Context types to inject as props.
 * @returns {HigherOrderComponent} A function that takes a component and returns a new component.
 * @example
 *
 * // Create a component that will bring back to home when clicked
 * const HomeButton = compose(
 *   withContext({router: PropTypes.object.isRequired}),
 *   withHandlers({onClick: ({router}) => () => router.push('/')}),
 * )('button');
 */
var getContext = function getContext(contextTypes) {
  return function (BaseComponent) {
    var factory = (0, _createEagerFactory2.default)(BaseComponent);
    var GetContext = function GetContext(ownerProps, context) {
      return factory(_extends({}, ownerProps, context));
    };

    GetContext.contextTypes = contextTypes;

    return GetContext;
  };
};

exports.default = (0, _createHelper2.default)(getContext, 'getContext');