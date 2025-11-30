'use strict';

exports.__esModule = true;

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

var _createHelper = require('./createHelper');

var _createHelper2 = _interopRequireDefault(_createHelper);

var _updateProps = require('./utils/updateProps');

var _updateProps2 = _interopRequireDefault(_updateProps);

var _callOrUse = require('./utils/callOrUse');

var _callOrUse2 = _interopRequireDefault(_callOrUse);

var _mapValues = require('./utils/mapValues');

var _mapValues2 = _interopRequireDefault(_mapValues);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/**
 * Takes an object map of handler creators or a factory function. These are
 * higher-order functions that accept a set of props and return a function handler:
 *
 * This allows the handler to access the current props via closure, without needing
 * to change its signature.
 *
 * Handlers are passed to the base component as immutable props, whose identities
 * are preserved across renders. This avoids a common pitfall where functional
 * components create handlers inside the body of the function, which results in a
 * new handler on every render and breaks downstream `shouldComponentUpdate()`
 * optimizations that rely on prop equality.
 *
 * @static
 * @category Higher-order-components
 * @param {Object|Function} handlerFactories
 * @returns {HigherOrderComponent} A function that takes a component and returns a new component.
 * @example
 *
 * const enhance = compose(
 *   withState('value', 'updateValue', ''),
 *   withHandlers({
 *     onChange: props => event => {
 *       props.updateValue(event.target.value)
 *     },
 *     onSubmit: props => event => {
 *       event.preventDefault()
 *       submitForm(props.value)
 *     }
 *   })
 * )
 *
 * const Form = enhance(({ value, onChange, onSubmit }) =>
 *   <form onSubmit={onSubmit}>
 *     <label>Value
 *       <input type="text" value={value} onChange={onChange} />
 *     </label>
 *   </form>
 * )
 */
var withHandlers = function withHandlers(handlerFactories) {
  return (0, _updateProps2.default)(function (next) {
    var cachedHandlers = void 0;
    var handlers = void 0;
    var props = void 0;

    var createHandlers = function createHandlers(initialProps) {
      return (0, _mapValues2.default)((0, _callOrUse2.default)(handlerFactories, initialProps), function (createHandler, handlerName) {
        return function () {
          var cachedHandler = cachedHandlers[handlerName];
          if (cachedHandler) {
            return cachedHandler.apply(undefined, arguments);
          }

          var handler = createHandler(props);
          cachedHandlers[handlerName] = handler;

          /* eslint-disable no-console */
          if (process.env.NODE_ENV !== 'production' && typeof handler !== 'function') {
            console.error(
            // eslint-disable-line no-console
            'withHandlers(): Expected a map of higher-order functions. ' + 'Refer to the docs for more info.');
          }
          /* eslint-enable no-console */

          return handler.apply(undefined, arguments);
        };
      });
    };

    return function (nextProps) {
      handlers = handlers || createHandlers(nextProps);
      cachedHandlers = {};
      props = nextProps;
      next(_extends({}, nextProps, handlers));
    };
  });
};

exports.default = (0, _createHelper2.default)(withHandlers, 'withHandlers');