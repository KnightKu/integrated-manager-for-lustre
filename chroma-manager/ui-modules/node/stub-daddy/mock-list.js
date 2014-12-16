//
// INTEL CONFIDENTIAL
//
// Copyright 2013-2015 Intel Corporation All Rights Reserved.
//
// The source code contained or described herein and all documents related
// to the source code ("Material") are owned by Intel Corporation or its
// suppliers or licensors. Title to the Material remains with Intel Corporation
// or its suppliers and licensors. The Material contains trade secrets and
// proprietary and confidential information of Intel or its suppliers and
// licensors. The Material is protected by worldwide copyright and trade secret
// laws and treaty provisions. No part of the Material may be used, copied,
// reproduced, modified, published, uploaded, posted, transmitted, distributed,
// or disclosed in any way without Intel's prior express written permission.
//
// No license under any patent, copyright, trade secret or other intellectual
// property right is granted to or conferred upon you by disclosure or delivery
// of the Materials, either expressly, by implication, inducement, estoppel or
// otherwise. Any license under such intellectual property rights must be
// express and approved by Intel in writing.

'use strict';

/**
 * Returns the mock state
 * @param {Object} requestStore
 * @param {Object} config
 * @param {Object} models
 * @returns {Function}
 */
exports.wiretree = function mockListModule(requestStore, config, models) {
  /**
   * Returns any error information contained in an object.
   * @returns {Object}
   */
  return function execute(request) {
    if (request.method === config.methods.GET) {

      return {
        status: config.status.SUCCESS,
        data: requestStore.getEntries(),
        headers: config.standardHeaders
      };
    }

    return new models.Response(config.status.BAD_REQUEST, config.standardHeaders);
  };
};