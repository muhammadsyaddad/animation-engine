'use strict';

exports.__esModule = true;

var _createEagerFactory = require('./createEagerFactory');

var _createEagerFactory2 = _interopRequireDefault(_createEagerFactory);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/**
 * Takes a component and returns a higher-order component version of that component.
 * This is useful in combination with another helper that expects a higher-order
 * component, like `branch`.
 *
 * @static
 * @category Higher-order-components
 * @param {ReactClass|ReactFunctionalComponent|String} Component
 * @returns {HigherOrderComponent} A function that takes a component and returns a new component.
 * @example
 *
 * const renderLoaderIfLoading = branch(
 *   ({loading} => loading),
 *   renderComponent(Loader),
 * )
 */
var renderComponent = function renderComponent(Component) {
  return function () {
    var factory = (0, _createEagerFactory2.default)(Component);
    var RenderComponent = function RenderComponent(props) {
      return factory(props);
    };
    if (process.env.NODE_ENV !== 'production') {
      /* eslint-disable global-require */
      var wrapDisplayName = require('./wrapDisplayName').default;
      /* eslint-enable global-require */
      RenderComponent.displayName = wrapDisplayName(Component, 'renderComponent');
    }
    return RenderComponent;
  };
};

exports.default = renderComponent;