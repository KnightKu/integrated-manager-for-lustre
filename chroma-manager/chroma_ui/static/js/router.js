

function uri_properties_link(resource_uri, label)
{
  if (resource_uri) {
    var url = resource_uri.replace("/api/", "/");
    return "<a class='navigation' href='" + url + "'>" + label + "</a>"
  } else {
    return ""
  }
}

function object_properties_link(object, label)
{
  if (!label) {
    label = LiveObject.label(object);
  }
  return uri_properties_link(object.resource_uri, label);
}

/* FIXME: if router callbacks throw an exception when called
 * as a result of Backbone.history.navigate({trigger:true}),
 * the exception isn't visible at the console, and the URL
 * just gets appended to window.location.href.  Is this a
 * backbone bug?  Should we override History to fix this?
 */
var ChromaRouter = Backbone.Router.extend({
  routes: {
    "configure/filesystem/detail/:id/": "filesystemDetail",
    "configure/filesystem/list/": "filesystemList",
    "configure/filesystem/create/": "filesystemCreate",
    "configure/:tab/": "configure",
    "configure/": "configureIndex",
    "dashboard/": "dashboard",
    "command/:id/": 'command_detail',
    "target/:id/": 'target_detail',
    "host/:id/": 'server_detail',
    "storage_resource/:id/": 'storage_resource_detail',
    "job/:id/": 'job_detail',
    "": "dashboard",
    "alert/": "alert",
    "event/": "event",
    "log/": "log"
  },
  object_detail: function(id, model_class, view_class, title_attr)
  {
    var c = new model_class({id: id});
    c.fetch({success: function(model, response) {
      var mydiv = $("<div style='overflow-y: scroll;'></div>");

      var title;
      if (title_attr){
        title = c.get(title_attr);
      } else {
        title = undefined;
      }
      mydiv.dialog({
        buttons: [{text: "Close", 'class': "close", click: function(){}}],
        width: 600,
        height: 600,
        modal: true,
        title: title,
        open: function(event, ui) {
          // Hide the window close button to have a single close handler
          // (the button) which manages history.
          mydiv.parent().find('.ui-dialog-titlebar-close').hide();
        }
      });
      var cd = new view_class({model: c, el: mydiv.parent()});
      cd.render();
    }})
  },
  command_detail: function(id)
  {
    this.object_detail(id, Command, CommandDetail);
  },
  target_detail: function(id)
  {
    this.object_detail(id, Target, TargetDetail, 'label');
  },
  storage_resource_detail: function(id)
  {
    this.object_detail(id, StorageResource, StorageResourceDetail, 'class_name');
  },
  job_detail: function(id) 
  {
    this.object_detail(id, StorageResource, StorageResourceDetail);
  },
  server_detail: function(id)
  {
    this.object_detail(id, Server, ServerDetail);
  },
  alert: function()
  {
    this.toplevel('alert');
  },
  event: function()
  {
    this.toplevel('event');
  },
  log: function()
  {
    this.toplevel('log');
  },
  configureIndex: function()
  {
    this.filesystemList()
  },
  toplevel: function(name)
  {
    $('div.toplevel').hide();
    $("#toplevel-" + name).show();

    $('a.navigation').removeClass('active');
    $("#" + name + "_menu").addClass('active');

    window.title = name + " - Chroma Server"

    if (name == 'alert') {
      AlertView.draw();
    } else if (name == 'event') {
      EventView.draw();
    } else if (name == 'log') {
      LogView.draw();
    }
  },
  configureTab: function(tab)
  {
    this.toplevel('configure');
    $("#tabs").tabs('select', '#' + tab + "-tab");
  },
  configure: function(tab) {
    this.configureTab(tab);
    if (tab == 'filesystem') {
      this.filesystemList();
    } else if (tab == 'server') {
      ServerView.draw()
    } else if (tab == 'volume') {
      VolumeView.draw()
    } else if (tab == 'user') {
      UserView.draw()
    } else if (tab == 'storage') {
      StorageView.draw()
    } else if (tab == 'mgt') {
      MgtView.draw()
    }
  },
  filesystemPage: function(page) {
    this.configureTab('filesystem')
    $('#filesystem-tab-list').hide()
    $('#filesystem-tab-create').hide()
    $('#filesystem-tab-detail').hide()
    $('#filesystem-tab-' + page).show()
  },
  filesystemList: function() {
    this.filesystemPage('list');
    FilesystemListView.draw()
  },
  filesystemDetail: function(id) {
    this.filesystemPage('detail');
    FilesystemDetailView.draw(id)
  },
  filesystemCreate: function() {
    this.filesystemPage('create');
    FilesystemCreateView.draw()
  },
  dashboard: function() {
    this.toplevel('dashboard');

    Dashboard.loadView(window.location.hash);
    $('#fsSelect').attr("value","");
    $('#intervalSelect').attr("value","");
  }
});
