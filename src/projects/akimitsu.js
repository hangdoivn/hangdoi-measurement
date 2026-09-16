export const akimitsu = {
  id: 'akimitsu',
  name: 'Tempura Akimitsu Da Nang',
  timezone: 'Asia/Ho_Chi_Minh',
  hosts: ['akimitsu.store', 'www.akimitsu.store', 'menu.akimitsu.store', 'go.akimitsu.store'],
  googleAdsCustomerId: '8681228450',
  location: {
    label: 'AKIMITSU - Binh Minh 5',
    googlePlaceId: 'ChIJeWHjMgAZQjER4Y_VVVTEsDY',
  },
  destinations: {
    menu: {
      provider: 'gurutto',
      url: 'https://jp.gurutto-vietnam.com/gourmet/tempura-akimitsudanang/',
      eventName: 'menu_click',
    },
    order: {
      provider: 'mmenu',
      url: 'https://api.mmenu.io/v2/url/OnkjI9',
      eventName: 'order_click',
    },
    maps: {
      provider: 'google_maps',
      url: 'https://www.google.com/maps/search/?api=1&query=Tempura%20Akimitsu%20Da%20Nang&query_place_id=ChIJeWHjMgAZQjER4Y_VVVTEsDY',
      eventName: 'direction_click',
    },
    call: {
      provider: 'phone',
      url: 'tel:+84973377246',
      eventName: 'call_click',
    },
  },
};

export const projects = new Map([[akimitsu.id, akimitsu]]);
