'use strict';

exports.__esModule = true;
var config = {
  observablesKey: 'observables'

  /**
   * Set the config of Recompact.
   *
   * @static
   * @category Config
   * @param {Object} options
   * @example
   *
   * setConfig({observablesKey: 'observables'});
   */
};var setConfig = function setConfig(_config) {
  config = _config;
};

var getConfig = exports.getConfig = function getConfig() {
  return config;
};

exports.default = setConfig;