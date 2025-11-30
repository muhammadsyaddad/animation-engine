'use strict';

exports.__esModule = true;

var _onlyUpdateForKeys = require('./onlyUpdateForKeys');

var _onlyUpdateForKeys2 = _interopRequireDefault(_onlyUpdateForKeys);

var _createHelper = require('./createHelper');

var _createHelper2 = _interopRequireDefault(_createHelper);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/**
 * Works like `onlyUpdateForKeys()`, but prop keys are inferred from the `propTypes`
 * of the base component. Useful in conjunction with `setPropTypes()`.
 *
 * If the base component does not have any `propTypes`, the component will never
 * receive any updates. This probably isn't the expected behavior, so a warning
 * is printed to the console.
 *
 * @static
 * @category Higher-order-components
 * @returns {HigherOrderComponent} A function that takes a component and returns a new component.
 * @see onlyUpdateForKeys
 * @example
 *
 * const Button = ({className}) => <button className={className} />;
 * Button.propTypes = {className: PropTypes.string};
 * const EnhancedButton = onlyUpdateForPropTypes(Button);
 */
var onlyUpdateForPropTypes = function onlyUpdateForPropTypes(BaseComponent) {
  var propTypes = BaseComponent.propTypes;


  if (process.env.NODE_ENV !== 'production') {
    /* eslint-disable global-require */
    var getDisplayName = require('./getDisplayName').default;
    /* eslint-enable global-require */
    if (!propTypes) {
      /* eslint-disable */
      console.error('A component without any `propTypes` was passed to ' + '`onlyUpdateForPropTypes()`. Check the implementation of the ' + ('component with display name "' + getDisplayName(BaseComponent) + '".'));
      /* eslint-enable */
    }
  }

  return (0, _onlyUpdateForKeys2.default)(Object.keys(propTypes || {}))(BaseComponent);
};

exports.default = (0, _createHelper2.default)(onlyUpdateForPropTypes, 'onlyUpdateForPropTypes', true, true);