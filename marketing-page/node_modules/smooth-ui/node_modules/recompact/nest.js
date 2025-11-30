'use strict';

exports.__esModule = true;

var _createEagerFactory = require('./createEagerFactory');

var _createEagerFactory2 = _interopRequireDefault(_createEagerFactory);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _objectWithoutProperties(obj, keys) { var target = {}; for (var i in obj) { if (keys.indexOf(i) >= 0) continue; if (!Object.prototype.hasOwnProperty.call(obj, i)) continue; target[i] = obj[i]; } return target; }

/**
 * Composes components by nesting each one inside the previous.
 *
 * @static
 * @category Higher-order-components
 * @param {...(ReactClass|ReactFunctionalComponent)} components
 * @returns {ReactFunctionalComponent}
 * @example
 *
 * // Delay rendering of 1s
 * const DivButton = nest('div', 'button');
 * // will render <div className="foo"><button className="foo" /></div>
 * <DivButton className="foo" />
 */
var nest = function nest() {
  for (var _len = arguments.length, components = Array(_len), _key = 0; _key < _len; _key++) {
    components[_key] = arguments[_key];
  }

  var factories = components.map(_createEagerFactory2.default);
  var Nest = function Nest(_ref) {
    var children = _ref.children,
        props = _objectWithoutProperties(_ref, ['children']);

    return factories.reduceRight(function (child, factory) {
      return factory(props, child);
    }, children);
  };

  if (process.env.NODE_ENV !== 'production') {
    /* eslint-disable global-require */
    var getDisplayName = require('./getDisplayName').default;
    /* eslint-enable global-require */
    var displayNames = components.map(getDisplayName);
    Nest.displayName = 'nest(' + displayNames.join(', ') + ')';
  }

  return Nest;
};

exports.default = nest;