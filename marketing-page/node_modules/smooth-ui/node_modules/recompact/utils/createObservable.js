'use strict';

exports.__esModule = true;

var _symbolObservable = require('symbol-observable');

var _symbolObservable2 = _interopRequireDefault(_symbolObservable);

var _setObservableConfig = require('../setObservableConfig');

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/* eslint-disable import/prefer-default-export */
var createObservable = function createObservable(subscribe) {
  var _obsConfig$fromESObse;

  return _setObservableConfig.config.fromESObservable((_obsConfig$fromESObse = {
    subscribe: subscribe
  }, _obsConfig$fromESObse[_symbolObservable2.default] = function () {
    return this;
  }, _obsConfig$fromESObse));
};

exports.default = createObservable;