'use strict';

exports.__esModule = true;
/**
 * Utility method that gives to higher-order components a comprehensive display name.
 *
 * @static
 * @category Utilities
 * @param {HigherOrderComponent} hoc Higher-order component to wrap.
 * @param {String} helperName Name used to create displayName.
 * @param {Boolean} [noArgs=false] Indicate if the higher-order component has some arguments.
 * @returns {HigherOrderComponent} Returns a wrapped hoc.
 * @example
 *
 * const pluckOnChangeTargetValue = createHelper(
 *   withHandlers({
 *     onChange: ({onChange}) => ({target: {value}}) => onChange(value),
 *   }),
 *   'pluckOnChangeTargetValue',
 * );
 *
 * const Input = pluckOnChangeTargetValue('input');
 * <Input /> // Will have "pluckOnChangeTargetValue(input)" as displayName
 */
var createHelper = function createHelper(hoc, helperName) {
  var setDisplayName = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : true;
  var noArgs = arguments.length > 3 && arguments[3] !== undefined ? arguments[3] : false;

  if (process.env.NODE_ENV !== 'production' && setDisplayName) {
    /* eslint-disable global-require */
    var wrapDisplayName = require('./wrapDisplayName').default;
    /* eslint-enable global-require */

    if (noArgs) {
      return function (BaseComponent) {
        var Component = hoc(BaseComponent);
        Component.displayName = wrapDisplayName(BaseComponent, helperName);
        return Component;
      };
    }

    return function () {
      for (var _len = arguments.length, args = Array(_len), _key = 0; _key < _len; _key++) {
        args[_key] = arguments[_key];
      }

      return function (BaseComponent) {
        var Component = hoc.apply(undefined, args)(BaseComponent);
        Component.displayName = wrapDisplayName(BaseComponent, helperName);
        return Component;
      };
    };
  }

  return hoc;
};

exports.default = createHelper;